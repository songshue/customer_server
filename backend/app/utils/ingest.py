#!/usr/bin/env python3
"""
文档摄取脚本 - RAG系统知识库构建
功能：加载文档 → 切分 → 向量化 → 存储到Chroma
"""
import os
import sys
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.vectorstores import Chroma
import logging
from dotenv import load_dotenv

load_dotenv()
# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentIngestor:
    """文档摄取器类"""
    
    def __init__(self, knowledge_dir="knowledge", collection_name="policy_documents"):
        """
        初始化文档摄取器
        
        Args:
            knowledge_dir: 知识文档目录
            collection_name: Chroma集合名称
        """
        self.knowledge_dir = Path(knowledge_dir)
        self.collection_name = collection_name
        self.vectorstore = None
        
        # 创建知识目录（如果不存在）
        self.knowledge_dir.mkdir(exist_ok=True)
        
        # 获取API密钥
        self.api_key = os.getenv("BAILIAN_API_KEY")
        if not self.api_key:
            logger.warning("未找到BAILIAN_API_KEY环境变量")
            logger.warning("将使用模拟嵌入进行演示")
    
    def load_documents(self):
        """加载所有支持的文档"""
        documents = []
        
        # 支持的文件类型和对应的加载器
        loaders = {
            ".pdf": PyPDFLoader,
            ".txt": TextLoader
        }
        
        for file_path in self.knowledge_dir.iterdir():
            if file_path.is_file() and file_path.suffix in loaders:
                try:
                    logger.info(f"正在加载文档: {file_path.name}")
                    
                    # 加载文档
                    loader_class = loaders[file_path.suffix]
                    if file_path.suffix == ".pdf":
                        loader = loader_class(str(file_path))
                    else:
                        loader = loader_class(str(file_path), encoding='utf-8')
                    
                    docs = loader.load()
                    
                    # 为每个文档添加元数据
                    for doc in docs:
                        doc.metadata = {
                            "source": file_path.name,
                            "file_type": file_path.suffix,
                            "file_path": str(file_path)
                        }
                    
                    documents.extend(docs)
                    logger.info(f"成功加载 {len(docs)} 个文档片段")
                    
                except Exception as e:
                    logger.error(f"加载文档 {file_path.name} 时出错: {e}")
        
        return documents
    
    def split_documents(self, documents, chunk_size=500, chunk_overlap=50):
        """切分文档为较小的片段"""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", "。", " ", ""]
        )
        
        split_docs = text_splitter.split_documents(documents)
        logger.info(f"文档切分为 {len(split_docs)} 个片段")
        
        return split_docs
    
    def create_embeddings(self):
        """创建嵌入模型"""
        if self.api_key:
            try:
                # 使用DashScopeEmbeddings
                embeddings = DashScopeEmbeddings(
                    model="text-embedding-v3",
                    dashscope_api_key=self.api_key
                )
                logger.info("使用DashScopeEmbeddings创建嵌入模型")
                logger.info("API密钥长度: " + str(len(self.api_key)))
                return embeddings
            except Exception as e:
                logger.error(f"创建DashScopeEmbeddings时出错: {e}")
        
        # 降级方案：使用模拟嵌入进行演示
        logger.warning("使用模拟嵌入进行演示")
        return MockEmbeddings()
    
    def create_vectorstore(self, documents):
        """创建向量数据库"""
        embeddings = self.create_embeddings()
        
        # 创建Chroma向量数据库
        vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            collection_name=self.collection_name,
            persist_directory="./chroma_db"
        )
        
        logger.info(f"成功创建向量数据库，集合名称: {self.collection_name}")
        self.vectorstore = vectorstore
        return vectorstore
    
    def ingest_all(self):
        """执行完整的文档摄取流程"""
        logger.info("开始文档摄取流程...")
        
        # 1. 加载文档
        logger.info("步骤1: 加载文档")
        documents = self.load_documents()
        if not documents:
            logger.error("未找到任何可加载的文档")
            return None
        
        # 2. 切分文档
        logger.info("步骤2: 切分文档")
        split_docs = self.split_documents(documents)
        
        # 3. 创建向量数据库
        logger.info("步骤3: 创建向量数据库")
        vectorstore = self.create_vectorstore(split_docs)
        
        # 4. 保存数据库
        logger.info("步骤4: 保存向量数据库")
        vectorstore.persist()
        
        logger.info("文档摄取完成！")
        return vectorstore
    
    def test_retrieval(self, query="退货政策", top_k=3):
        """测试检索功能"""
        if not self.vectorstore:
            logger.error("向量数据库未初始化")
            return None
        
        logger.info(f"测试检索: '{query}'")
        docs = self.vectorstore.similarity_search(query, k=top_k)
        
        for i, doc in enumerate(docs, 1):
            logger.info(f"检索结果 {i}:")
            logger.info(f"内容: {doc.page_content[:100]}...")
            logger.info(f"来源: {doc.metadata.get('source', 'Unknown')}")
            logger.info("---")
        
        return docs


class MockEmbeddings:
    """模拟嵌入类 - 生成1024维向量以匹配text-embedding-v3"""
    
    def embed_query(self, text):
        """模拟查询嵌入"""
        # 生成1024维的向量
        import hashlib
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
        """模拟文档嵌入"""
        return [self.embed_query(text) for text in texts]


def main():
    """主函数"""
    # 创建摄取器实例
    ingestor = DocumentIngestor()
    
    # 执行摄取流程
    vectorstore = ingestor.ingest_all()
    
    if vectorstore:
        # 测试检索功能
        test_queries = ["退货政策", "客服时间", "退款流程"]
        for query in test_queries:
            print(f"\n=== 测试查询: {query} ===")
            ingestor.test_retrieval(query)
        
        print(f"\n向量数据库已保存到 ./chroma_db 目录")
        print("文档摄取完成！")


if __name__ == "__main__":
    main()