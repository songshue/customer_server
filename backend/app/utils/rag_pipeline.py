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
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
# 导入LLM配置
from app.services.llm_config import create_llm_with_custom_config
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.messages import HumanMessage, AIMessage
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
    
    def __init__(self, collection_name="policy_documents"):
        """
        初始化RAG管道
        
        Args:
            collection_name: Chroma集合名称
        """
        self.collection_name = collection_name
        self.vectorstore = None
        self.llm = None
        self.embeddings = None
        
        # 初始化组件
        self._initialize_components()
    
    def _initialize_components(self):
        """初始化RAG管道组件"""
        try:
            # 1. 初始化嵌入模型
            api_key = os.getenv("BAILIAN_API_KEY")
            if api_key:
                self.embeddings = DashScopeEmbeddings(
                    model="text-embedding-v3",
                    dashscope_api_key=api_key
                )
                logger.info("使用DashScopeEmbeddings嵌入模型")
                logger.info(f"API密钥长度: {len(api_key)}")
            else:
                logger.warning("未找到API密钥，使用模拟嵌入")
                self.embeddings = MockEmbeddings()
            
            # 2. 加载向量数据库
            # 使用绝对路径确保正确加载
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            chroma_db_path = os.path.join(base_dir, "chroma_db")
            
            # 确保目录存在
            os.makedirs(chroma_db_path, exist_ok=True)
            
            logger.info(f"向量数据库路径: {chroma_db_path}")
            
            # 检查数据库是否为空
            try:
                temp_vectorstore = Chroma(
                    collection_name=self.collection_name,
                    persist_directory=chroma_db_path,
                    embedding_function=self.embeddings
                )
                
                # 尝试获取文档数量
                doc_count = temp_vectorstore._collection.count()
                logger.info(f"向量数据库中有 {doc_count} 个文档")
                
                # 如果数据库为空，提供建议
                if doc_count == 0:
                    logger.warning("向量数据库为空！请先运行 ingest.py 来加载文档。")
                    logger.warning(f"运行命令: python {os.path.join(base_dir, 'backend', 'ingest.py')}")
                
                self.vectorstore = temp_vectorstore
            except Exception as e:
                logger.error(f"加载向量数据库时出错: {e}")
                raise
            
            logger.info(f"成功加载向量数据库: {self.collection_name}")
            
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
                
        except Exception as e:
            logger.error(f"初始化RAG管道失败: {e}")
            raise
    
    def retrieve_documents(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        检索相关文档
        
        Args:
            query: 用户查询
            top_k: 返回文档数量
            
        Returns:
            检索到的文档列表
        """
        try:
            # 添加详细日志
            logger.info(f"开始检索文档，查询: {query}")
            logger.info(f"向量数据库状态: {self.get_knowledge_stats()}")
            
            # 执行相似性搜索
            docs = self.vectorstore.similarity_search(query, k=top_k)
            logger.info(f"原始检索结果: {docs}")
            
            results = []
            for i, doc in enumerate(docs):
                result = {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": getattr(doc, 'score', None)  # 如果有相似度分数
                }
                results.append(result)
                logger.info(f"文档 {i+1}: 预览内容={result['content'][:50]}..., 源文件={result['metadata'].get('source', '未知')}")
            
            logger.info(f"检索到 {len(results)} 个相关文档")
            return results
            
        except Exception as e:
            logger.error(f"文档检索失败: {e}")
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
            return "抱歉，我没有找到相关的政策信息。请提供更多详细信息或联系客服。"
        
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
            return "抱歉，我没有找到相关的政策信息。请提供更多详细信息或联系客服。"
        
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

        请遵循以下要求：
        1. 基于文档内容准确回答问题
        2. 如果文档中没有相关信息，请说明
        3. 回答要专业、友好
        4. 引用具体的政策条款
        5. 如果涉及具体操作指引，请详细说明

        回答："""
        return prompt
    
    async def process_message(self, message: str, session_id: str = None, 
                            conversation_context: List[Dict] = None) -> Dict[str, Any]:
        """
        处理用户消息的完整流程（支持缓存、MySQL存储和日志记录）
        
        Args:
            message: 用户消息
            session_id: 会话ID
            conversation_context: 对话历史上下文
            
        Returns:
            包含回答和引用信息的字典
        """
        start_time = time.time()
        logger.info(f"处理用户消息: {message}")
        
        # 记录消息到会话
        if session_id:
            await session_manager.add_message_to_context(session_id, "user", message)
        
        try:
            # 1. 检查是否为热门问题（缓存命中）
            logger.info(f"开始检查缓存: {message[:30]}...")
            if redis_manager:
                cached_response = await redis_manager.get_cached_response(message)
                logger.info(f"Redis管理器状态: 已连接")
            else:
                cached_response = None
                logger.warning("Redis管理器未初始化")
                
            if cached_response:
                logger.info(f"命中缓存，直接返回回复: {message[:30]}...")
                logger.info(f"缓存内容: {cached_response.get('response', '')[:50]}...")
                
                # 保存缓存命中的记录到MySQL
                try:
                    if mysql_manager:
                        await mysql_manager.save_message(
                            session_id=session_id or "unknown",
                            user_id="user",
                            role="user",
                            content=message,
                            metadata={"cache_hit": True, "query": message}
                        )
                        await mysql_manager.save_message(
                            session_id=session_id or "unknown",
                            user_id="ai",
                            role="assistant",
                            content=cached_response["response"],
                            metadata={"cache_hit": True, "cached_time": cached_response["timestamp"]}
                        )
                except Exception as e:
                    logger.error(f"保存缓存消息到MySQL失败: {e}")
                except ImportError:
                    pass
                
                # 记录消息到会话
                if session_id:
                    await session_manager.add_message_to_context(session_id, "assistant", cached_response["response"])
                
                return {
                    "response": cached_response["response"],
                    "references": [],  # 缓存的回复通常不包含引用
                    "query": message,
                    "session_id": session_id,
                    "has_knowledge": True,
                    "processing_time": time.time() - start_time,
                    "cache_hit": True,
                    "cached_time": cached_response["timestamp"]
                }
            else:
                logger.info(f"缓存未命中，继续正常处理: {message[:30]}...")
            
            # 2. 正常RAG处理流程（非缓存）
            # 检索相关文档
            retrieved_docs = self.retrieve_documents(message, top_k=3)
            
            # 构建对话上下文（如果需要）
            context_prompt = ""
            if conversation_context:
                context_prompt = await session_manager.build_prompt_with_context(conversation_context)
            
            # 生成回答
            response = await self.generate_response_with_context(
                message, retrieved_docs, context_prompt, conversation_context
            )
            
            # 3. 缓存热门问答（优化的缓存策略）
            logger.info(f"缓存检查: retrieved_docs={len(retrieved_docs) if retrieved_docs else 0}, response_length={len(response)}")
            
            # 扩展热门问题关键词列表
            hot_keywords = [
                "退货", "退换货", "退款", "政策", "流程", "条件", "要求",
                "售后", "客服", "联系方式", "地址", "电话", "营业时间",
                "配送", "运费", "快递", "包邮", "发货",
                "支付", "付款", "信用卡", "支付宝", "微信支付",
                "会员", "积分", "优惠券", "折扣", "活动",
                "商品", "产品", "库存", "价格", "规格",
                "质量", "保证", "保修", "维修", "更换"
            ]
            
            matched_keywords = [kw for kw in hot_keywords if kw in message]
            logger.info(f"热门关键词匹配: {matched_keywords}")
            
            # 缓存条件判断（更宽松的策略）
            should_cache = False
            cache_reason = ""
            
            # 条件1：有检索到的文档且回复内容合适
            if retrieved_docs and len(response) > 10:
                should_cache = True
                cache_reason = f"有相关文档且回复合适({len(response)}字符)"
            
            # 条件2：包含热门关键词且回复内容合理
            elif any(keyword in message for keyword in hot_keywords) and len(response) > 5:
                should_cache = True
                cache_reason = f"热门关键词匹配，回复内容合理({len(response)}字符)"
            
            # 条件3：回复内容较长（通用质量标准）
            elif len(response) > 50:
                should_cache = True
                cache_reason = f"回复内容较长，质量较高({len(response)}字符)"
            
            if should_cache:
                if redis_manager:
                    cache_success = await redis_manager.cache_response(message, response, ttl=300)
                    if cache_success:
                        logger.info(f"已缓存问答: {message[:30]}... (原因: {cache_reason})")
                    else:
                        logger.error(f"缓存问答失败: {message[:30]}...")
                else:
                    logger.warning("Redis管理器未初始化，无法缓存问答")
            else:
                logger.info(f"不缓存此回复: {message[:30]}... (原因: {cache_reason or '不满足缓存条件'})")
            
            # 4. 构建引用信息
            references = []
            for doc in retrieved_docs:
                source = doc.get("metadata", {}).get("source", "未知来源")
                references.append({
                    "source": source,
                    "content_preview": doc["content"][:100] + "..." if len(doc["content"]) > 100 else doc["content"]
                })
            
            # 5. 保存到MySQL
            try:
                if mysql_manager:
                    await mysql_manager.save_message(
                        session_id=session_id or "unknown",
                        user_id="user",
                        role="user",
                        content=message,
                        metadata={"retrieved_docs": len(retrieved_docs), "query": message}
                    )
                    await mysql_manager.save_message(
                        session_id=session_id or "unknown",
                        user_id="ai",
                        role="assistant",
                        content=response,
                        metadata={"has_references": len(references) > 0, "references": references}
                    )
            except Exception as e:
                logger.error(f"保存消息到MySQL失败: {e}")
            except ImportError:
                pass
            
            # 6. 记录对话到日志
            if session_id:
                await logger_manager.log_chat_message(
                    session_id=session_id,
                    user_id="user",
                    role="user",
                    content=message,
                    metadata={"query": message, "retrieved_docs": len(retrieved_docs)}
                )
                
                await logger_manager.log_chat_message(
                    session_id=session_id,
                    user_id="ai",
                    role="assistant", 
                    content=response,
                    metadata={"has_references": len(references) > 0, "references": references}
                )
                
                # 记录RAG查询信息
                await logger_manager.log_rag_query(
                    session_id=session_id,
                    query=message,
                    retrieved_docs=len(retrieved_docs),
                    processing_time=time.time() - start_time,
                    has_references=len(references) > 0
                )
            
            # 7. 返回结果
            result = {
                "response": response,
                "references": references,
                "query": message,
                "session_id": session_id,
                "has_knowledge": len(retrieved_docs) > 0,
                "processing_time": time.time() - start_time,
                "cache_hit": False
            }
            
            # 记录助手回复到会话
            if session_id:
                await session_manager.add_message_to_context(session_id, "assistant", response)
            
            return result
            
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
            
            # 即使出错也要保存到MySQL和记录日志
            try:
                if mysql_manager:
                    await mysql_manager.save_message(
                        session_id=session_id or "unknown",
                        user_id="user",
                        role="user",
                        content=message,
                        metadata={"error": str(e), "query": message}
                    )
                    await mysql_manager.save_message(
                        session_id=session_id or "unknown",
                        user_id="ai",
                        role="assistant",
                        content=f"抱歉，处理您的问题时出现错误: {e}",
                        metadata={"error": str(e)}
                    )
            except Exception as mysql_error:
                logger.error(f"保存错误信息到MySQL失败: {mysql_error}")
            
            # 记录错误日志
            if session_id:
                await logger_manager.log_error(
                    error_type="RAG_PROCESSING",
                    error_message=str(e),
                    context={"session_id": session_id, "message": message}
                )
            
            return {
                "response": f"抱歉，处理您的问题时出现错误: {e}",
                "references": [],
                "query": message,
                "session_id": session_id,
                "has_knowledge": False,
                "error": str(e)
            }
    
    def get_knowledge_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        try:
            # 使用count()方法获取文档总数
            count = self.vectorstore._collection.count()
            
            # 获取嵌入函数信息
            embedding_info = "DashScopeEmbeddings" if isinstance(self.embeddings, DashScopeEmbeddings) else "MockEmbeddings"
            
            # 获取向量数据库路径
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            chroma_db_path = os.path.join(base_dir, "chroma_db")
            
            return {
                "total_documents": count,
                "collection_name": self.collection_name,
                "vectorstore_path": chroma_db_path,
                "embedding_model": embedding_info,
                "is_vectorstore_loaded": self.vectorstore is not None
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}
    
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
            # 使用向量数据库进行相似性搜索
            docs = self.vectorstore.similarity_search(query, k=top_k)
            logger.info(f"异步检索到 {len(docs)} 个相关文档")
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
    """模拟嵌入类 - 生成1024维向量以匹配text-embedding-v3"""
    
    def embed_query(self, text):
        import hashlib
        import math
        
        # 生成1024维的向量
        hash_val = hashlib.md5(text.encode()).digest()
        vector = []
        
        # 使用哈希值生成1024维的向量
        for i in range(1024):
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