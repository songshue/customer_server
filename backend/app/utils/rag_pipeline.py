#!/usr/bin/env python3
"""
RAG管道实现 - 基于LangChain的检索增强生成系统
功能：用户消息 → 检索相关文档 → 生成带引用的回答
"""
import os
import sys
import logging
import time
from typing import List, Dict, Any, Optional
from langchain_community.embeddings import DashScopeEmbeddings
from app.services.llm_config import create_llm_with_custom_config
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.messages import HumanMessage, AIMessage
from langchain_core.documents import Document
import json
from dotenv import load_dotenv
load_dotenv()

# 确保当前目录在Python路径中
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 导入会话管理和日志管理器
try:
    from ..managers.session_manager import session_manager
    from ..managers.logger_manager import logger_manager
    from ..managers.redis_manager import redis_manager
    from ..managers.mysql_manager import mysql_manager
except ImportError as e:
    logging.warning(f"导入管理器模块失败: {e}")
    # 创建空对象防止程序崩溃
    session_manager = None
    logger_manager = None
    redis_manager = None

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGPipeline:
    """RAG管道类 - 检索增强生成"""
    
    def __init__(self, collection_name="customer_policy"):
        """
        初始化RAG管道
        
        Args:
            collection_name: Qdrant集合名称
        """
        self.collection_name = collection_name
        self.vectorstore = None
        self.llm = None
        self.embeddings = None
        self._initialized = False
        self._init_error = None
        
        # 初始化组件
        self._initialize_components()
    
    def _initialize_components(self):
        """初始化RAG管道组件"""
        try:
            # 1. 初始化嵌入模型 - 支持多个环境变量名称
            api_key = (os.getenv("DASHSCOPE_API_KEY") or 
                      os.getenv("BAILIAN_API_KEY") or 
                      os.getenv("OPENAI_API_KEY"))
            
            if api_key:
                self.embeddings = DashScopeEmbeddings(
                    model="text-embedding-v2",
                    dashscope_api_key=api_key
                )
                logger.info("使用DashScopeEmbeddings嵌入模型")
                logger.info(f"API密钥长度: {len(api_key)}")
            else:
                logger.warning("未找到API密钥（DASHSCOPE_API_KEY/BAILIAN_API_KEY），使用模拟嵌入")
                self.embeddings = MockEmbeddings()
            
            # 2. 加载向量数据库 - 使用Qdrant
            try:
                from app.services.knowledge_base import QdrantVectorStore
                
                self.vectorstore = QdrantVectorStore(
                    collection_name=self.collection_name
                )
                logger.info(f"成功加载Qdrant向量数据库: {self.collection_name}")
                
            except ImportError as e:
                logger.error(f"无法导入QdrantVectorStore: {e}")
                self.vectorstore = None
            except Exception as e:
                logger.error(f"加载Qdrant向量数据库失败: {e}")
                self.vectorstore = None
            
            # 3. 初始化LLM（使用统一的LLM配置）
            try:
                # 使用统一的LLM配置
                self.llm = create_llm_with_custom_config(
                    temperature=0.1,
                    max_tokens=1000
                )
                
                if self.llm:
                    logger.info("初始化真实LLM模型")
                else:
                    logger.warning("未找到API密钥或配置，使用模拟模式")
                    self.llm = MockLLM()
            except Exception as e:
                logger.warning(f"初始化LLM失败: {e}，将使用模拟模式")
                self.llm = MockLLM()
            
            self._initialized = True
            logger.info(f"RAG管道初始化完成，Collection: {self.collection_name}")
                
        except Exception as e:
            logger.error(f"初始化RAG管道失败: {e}")
            self._init_error = str(e)
            self._initialized = False
    
    def is_available(self) -> Dict[str, Any]:
        """
        检查RAG管道是否可用
        
        Returns:
            可用性状态
        """
        return {
            "initialized": self._initialized,
            "collection_name": self.collection_name,
            "vectorstore_available": self.vectorstore is not None,
            "embeddings_available": self.embeddings is not None,
            "llm_available": self.llm is not None,
            "error": self._init_error
        }
    
    def retrieve_documents(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        检索相关文档
        
        Args:
            query: 用户查询
            top_k: 返回文档数量
            
        Returns:
            检索到的文档列表
        """
        try:
            logger.info(f"开始检索文档，查询: {query}, top_k: {top_k}")
            logger.info(f"RAG管道状态: {self.is_available()}")
            
            if not self.vectorstore:
                logger.error("向量数据库未初始化，无法检索文档")
                return []
            
            docs = self.vectorstore.search_knowledge(query, limit=top_k)
            logger.info(f"知识库搜索返回 {len(docs)} 个文档")
            
            results = []
            for i, doc in enumerate(docs):
                result = {
                    "content": doc['content'],
                    "metadata": {
                        "source": doc['source'],
                        "section": doc.get('section', '')
                    },
                    "score": doc['score']
                }
                results.append(result)
                logger.info(f"文档 {i+1}: 相似度分数={result['score']}, 源文件={result['metadata'].get('source', '未知')}")
                logger.debug(f"文档 {i+1} 内容预览: {result['content'][:100]}...")
            
            logger.info(f"成功检索到 {len(results)} 个相关文档")
            return results
            
        except Exception as e:
            logger.error(f"文档检索失败: {e}", exc_info=True)
            return []
    
    def generate_response(self, query: str, retrieved_docs: List[Dict]) -> str:
        """
        基于检索的文档生成回答
        
        Args:
            query: 用户查询
            retrieved_docs: 检索到的文档
            
        Returns:
            生成的回答
        """
        if not retrieved_docs:
            return "未在知识库中找到与您问题相关的信息。\n\n💡 建议：\n• 请尝试重新描述您的问题\n• 如果涉及具体订单或物流，请提供订单号或快递单号\n• 您也可以直接联系客服热线：400-123-4567 获取人工帮助"
        
        try:
            # 构建上下文
            context = self._build_context(retrieved_docs)
            
            # 构建提示词
            prompt = self._build_prompt(query, context)
            
            # 调用LLM生成回答
            if isinstance(self.llm, MockLLM):
                # 模拟LLM回答
                response = self.llm.generate(prompt, retrieved_docs)
            else:
                # 真实LLM调用
                messages = [HumanMessage(content=prompt)]
                response = self.llm.invoke(messages)
                response = response.content
            
            return response
            
        except Exception as e:
            logger.error(f"生成回答失败: {e}")
            return f"处理您的问题时出现错误: {e}"
    
    def _build_context(self, docs: List[Dict]) -> str:
        """构建检索文档的上下文"""
        context_parts = []
        
        for i, doc in enumerate(docs, 1):
            source = doc.get("metadata", {}).get("source", f"文档{i}")
            content = doc["content"]
            context_parts.append(f"=== {source} ===\n{content}")
        
        return "\n\n".join(context_parts)
    
    async def generate_response_with_context(self, query: str, retrieved_docs: List[Dict], 
                                           context_prompt: str = "", 
                                           conversation_context: List[Dict] = None) -> str:
        """
        基于检索的文档和会话上下文生成回答
        
        Args:
            query: 用户查询
            retrieved_docs: 检索到的文档
            context_prompt: 会话上下文提示词
            conversation_context: 对话历史上下文
            
        Returns:
            生成的回答
        """
        if not retrieved_docs:
            return "未在知识库中找到与您问题相关的信息。\n\n💡 建议：\n• 请尝试重新描述您的问题\n• 如果涉及具体订单或物流，请提供订单号或快递单号\n• 您也可以直接联系客服热线：400-123-4567 获取人工帮助"
        
        try:
            # 构建文档上下文
            context = self._build_context(retrieved_docs)
            
            # 构建提示词
            if conversation_context and context_prompt:
                # 有会话上下文的情况
                prompt = f"""{context_prompt}

                基于以下相关政策文档回答：
                {context}

                请提供准确、专业的回答，并引用具体的政策条款。"""
            else:
                # 没有会话上下文的情况
                prompt = self._build_prompt(query, context)
            
            # 调用LLM生成回答
            if isinstance(self.llm, MockLLM):
                # 模拟LLM回答
                response = self.llm.generate(prompt, retrieved_docs)
            else:
                # 真实LLM调用
                messages = [HumanMessage(content=prompt)]
                response = self.llm.invoke(messages)
                response = response.content
            
            return response
            
        except Exception as e:
            logger.error(f"生成上下文回答失败: {e}")
            return f"处理您的问题时出现错误: {e}"
    
    def _build_prompt(self, query: str, context: str) -> str:
        """构建提示词"""
        prompt = f"""你是客服助手，请根据以下政策文档回答用户问题。

用户问题：{query}

相关政策文档：
{context}

请遵循以下严格要求：
1. 只能基于提供的文档内容回答问题
2. 如果文档中没有相关信息，必须明确告知用户"未在知识库中找到相关内容"
3. 严格禁止编造、推测或虚构任何不在文档中的信息
4. 回答要专业、友好
5. 引用具体的政策条款（如果有）
6. 如果涉及具体操作指引，请详细说明（基于文档内容）

回答："""
        return prompt
    
    async def process_message(self, message: str, session_id: str = None, 
                            conversation_context: List[Dict] = None) -> Dict[str, Any]:
        """
        处理用户消息的流程 - 仅作为信息检索工具
        
        Args:
            message: 用户消息
            session_id: 会话ID
            conversation_context: 对话历史上下文
            
        Returns:
            包含检索到的文档和引用信息的字典
        """
        start_time = time.time()
        logger.info(f"处理用户消息: {message}")
        
        try:
            # 1. 检索相关文档
            retrieved_docs = self.retrieve_documents(message, top_k=5)
            
            # 在控制台输出检索到的信息，方便调试
            print("\n=== 向量知识库检索结果 ===")
            print(f"查询: {message}")
            print(f"检索到文档数量: {len(retrieved_docs)}")
            
            for i, doc in enumerate(retrieved_docs, 1):
                print(f"\n文档 {i}:")
                print(f"相似度分数: {doc.get('score', '未知')}")
                print(f"源文件: {doc.get('metadata', {}).get('source', '未知')}")
                print(f"内容: {doc['content'][:200]}{'...' if len(doc['content']) > 200 else ''}")
            
            print("==========================\n")
            
            # 2. 构建引用信息
            references = []
            for doc in retrieved_docs:
                source = doc.get("metadata", {}).get("source", "未知来源")
                references.append({
                    "source": source,
                    "content_preview": doc["content"][:100] + "..." if len(doc["content"]) > 100 else doc["content"],
                    "score": doc.get("score", None)
                })
            
            # 3. 返回结果
            result = {
                "documents": retrieved_docs,  # 返回原始检索文档
                "references": references,     # 简化的引用信息
                "query": message,
                "session_id": session_id,
                "has_knowledge": len(retrieved_docs) > 0,
                "processing_time": time.time() - start_time,
                "retrieved_count": len(retrieved_docs)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
            return {
                "documents": [],
                "references": [],
                "query": message,
                "session_id": session_id,
                "has_knowledge": False,
                "error": str(e)
            }
    
    def get_knowledge_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        try:
            from app.services.knowledge_base import QdrantVectorStore
            
            qdrant_store = QdrantVectorStore(collection_name=self.collection_name)
            collections = qdrant_store.client.get_collections()
            collection_info = next((c for c in collections.collections if c.name == self.collection_name), None)
            
            count = collection_info.points_count if collection_info else 0
            
            embedding_info = "DashScopeEmbeddings" if isinstance(self.embeddings, DashScopeEmbeddings) else "MockEmbeddings"
            
            return {
                "total_documents": count,
                "collection_name": self.collection_name,
                "vectorstore_type": "Qdrant",
                "host": qdrant_store.host,
                "port": qdrant_store.port,
                "embedding_model": embedding_info,
                "is_vectorstore_loaded": self.vectorstore is not None
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {
                "has_knowledge": False,
                "error": str(e)
            }
    
    async def aget_relevant_documents(self, query: str, top_k: int = 3):
        """
        异步获取相关文档（与LangChain接口兼容）
        
        Args:
            query: 查询字符串
            top_k: 返回文档数量
            
        Returns:
            相关文档列表
        """
        try:
            # 使用向量数据库进行知识库搜索
            results = self.vectorstore.search_knowledge(query, limit=top_k)
            logger.info(f"异步检索到 {len(results)} 个相关文档")
            
            # 将搜索结果转换为Document对象以保持与LangChain接口兼容
            from langchain_core.documents import Document
            docs = []
            for result in results:
                doc = Document(
                    page_content=result['content'],
                    metadata={
                        'source': result['source'],
                        'section': result.get('section', ''),
                        'score': result['score']
                    }
                )
                docs.append(doc)
            
            return docs
        except Exception as e:
            logger.error(f"异步检索文档失败: {e}")
            return []


class MockLLM:
    """模拟LLM类 - 用于演示"""
    
    def generate(self, prompt: str, retrieved_docs: List[Dict]) -> str:
        """模拟生成回答"""
        # 简单的规则生成回答
        if "退货" in prompt or "退换货" in prompt:
            if retrieved_docs:
                source = retrieved_docs[0].get("metadata", {}).get("source", "政策文档")
                return f"根据{source}，商品收到后7天内可申请退换货。商品必须保持原包装完整，未经使用。具体流程：\n1. 联系客服提出退换货申请\n2. 提供订单号和退换货原因\n3. 客服审核通过后提供退货地址\n4. 客户寄回商品并提供快递单号\n5. 仓库收到商品后3个工作日内处理"
            else:
                return "关于退换货政策，建议您联系我们的客服获得详细信息。"
        
        elif "客服时间" in prompt or "工作时间" in prompt:
            return "我们的客服时间为：工作日9:00-18:00。紧急情况有24小时响应机制，节假日期间也提供值班服务。"
        
        elif "退款" in prompt:
            return "退款说明：退款将在收到商品后5-7个工作日内处理，原路返回支付方式。运费一般不予退还（质量问题除外）。"
        
        else:
            return "感谢您的咨询。建议您提供更具体的问题，我将根据政策文档为您提供准确的信息。"
    
    def invoke(self, messages):
        """模拟LLM调用"""
        class MockResponse:
            def __init__(self, content):
                self.content = content
        
        prompt = messages[0].content
        response = self.generate(prompt, [])
        return MockResponse(response)


class MockEmbeddings:
    """模拟嵌入类 - 生成1536维向量以匹配text-embedding-v2"""
    
    def embed_query(self, text):
        import hashlib
        import math
        
        # 生成1536维的向量
        hash_val = hashlib.md5(text.encode()).digest()
        vector = []
        
        # 使用哈希值生成1536维的向量
        for i in range(1536):
            byte_val = hash_val[i % len(hash_val)]
            # 生成-1到1之间的值
            value = (byte_val / 255.0) * 2 - 1
            vector.append(value)
        
        return vector
    
    def embed_documents(self, texts):
        return [self.embed_query(text) for text in texts]


def main():
    """主函数 - 测试RAG管道"""
    # 创建RAG管道实例
    rag = RAGPipeline()
    
    # 获取知识库统计
    stats = rag.get_knowledge_stats()
    print(f"知识库统计: {stats}")
    
    # 测试消息
    test_messages = [
        "我想要退货，需要什么条件？",
        "客服什么时候上班？",
        "退款需要多长时间？",
        "我可以换货吗？"
    ]
    
    print("\n=== RAG管道测试 ===")
    for message in test_messages:
        print(f"\n用户: {message}")
        result = rag.process_message(message)
        print(f"AI: {result['response']}")
        print(f"引用: {len(result['references'])} 个文档")
        for ref in result['references']:
            print(f"  - {ref['source']}")


if __name__ == "__main__":
    main()