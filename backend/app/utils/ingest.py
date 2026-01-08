#!/usr/bin/env python3
"""
文档摄取脚本 - RAG系统知识库构建
功能：加载文档 → 切分 → 向量化 → 存储到Qdrant
"""
import os
import sys
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import DashScopeEmbeddings
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentIngestor:
    """文档摄取器类"""

    def __init__(self, knowledge_dir="knowledge", collection_name="policy_documents"):
        """
        初始化文档摄取器

        Args:
            knowledge_dir: 知识文档目录
            collection_name: Qdrant集合名称
        """
        self.knowledge_dir = Path(knowledge_dir)
        self.collection_name = collection_name
        self.vectorstore = None

        self.knowledge_dir.mkdir(exist_ok=True)

        self.api_key = os.getenv("BAILIAN_API_KEY")
        if not self.api_key:
            logger.warning("未找到BAILIAN_API_KEY环境变量")
            logger.warning("将使用模拟嵌入进行演示")

    def load_documents(self):
        """加载所有支持的文档"""
        documents = []

        loaders = {
            ".pdf": PyPDFLoader,
            ".txt": TextLoader
        }

        for file_path in self.knowledge_dir.iterdir():
            if file_path.is_file() and file_path.suffix in loaders:
                try:
                    logger.info(f"正在加载文档: {file_path.name}")

                    loader_class = loaders[file_path.suffix]
                    if file_path.suffix == ".pdf":
                        loader = loader_class(str(file_path))
                    else:
                        loader = loader_class(str(file_path), encoding='utf-8')

                    docs = loader.load()

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
                embeddings = DashScopeEmbeddings(
                    model="text-embedding-v2",
                    dashscope_api_key=self.api_key
                )
                logger.info("使用DashScopeEmbeddings创建嵌入模型")
                logger.info("API密钥长度: " + str(len(self.api_key)))
                return embeddings
            except Exception as e:
                logger.error(f"创建DashScopeEmbeddings时出错: {e}")

        logger.warning("使用模拟嵌入进行演示")
        return MockEmbeddings()

    def create_vectorstore(self, documents):
        """创建向量数据库"""
        from app.services.knowledge_base import QdrantVectorStore

        embeddings = self.create_embeddings()

        qdrant_store = QdrantVectorStore(
            collection_name=self.collection_name
        )

        for doc in documents:
            qdrant_store.add_text(
                text=doc.page_content,
                metadata=doc.metadata
            )

        logger.info(f"成功创建Qdrant向量数据库，集合名称: {self.collection_name}")
        self.vectorstore = qdrant_store
        return vectorstore

    def ingest_all(self):
        """执行完整的文档摄取流程"""
        logger.info("开始文档摄取流程...")

        logger.info("步骤1: 加载文档")
        documents = self.load_documents()
        if not documents:
            logger.error("未找到任何可加载的文档")
            return None

        logger.info("步骤2: 切分文档")
        split_docs = self.split_documents(documents)

        logger.info("步骤3: 创建向量数据库")
        self.create_vectorstore(split_docs)

        logger.info("文档摄取完成！")
        return self.vectorstore

    def test_retrieval(self, query="退货政策", top_k=3):
        """测试检索功能"""
        if not self.vectorstore:
            logger.error("向量数据库未初始化")
            return None

        logger.info(f"测试检索: '{query}'")
        results = self.vectorstore.search_knowledge(query, limit=top_k)

        for i, result in enumerate(results, 1):
            logger.info(f"检索结果 {i}:")
            logger.info(f"内容: {result['content'][:100]}...")
            logger.info(f"来源: {result['source']}")
            logger.info(f"相似度: {result['score']}")
            logger.info("---")

        return results


class MockEmbeddings:
    """模拟嵌入类 - 生成1536维向量以匹配text-embedding-v2"""

    def embed_query(self, text):
        import hashlib

        hash_val = hashlib.md5(text.encode()).digest()
        vector = []

        for i in range(1536):
            byte_val = hash_val[i % len(hash_val)]
            value = (byte_val / 255.0) * 2 - 1
            vector.append(value)

        return vector

    def embed_documents(self, texts):
        return [self.embed_query(text) for text in texts]


def main():
    """主函数"""
    ingestor = DocumentIngestor()

    vectorstore = ingestor.ingest_all()

    if vectorstore:
        test_queries = ["退货政策", "客服时间", "退款流程"]
        for query in test_queries:
            print(f"\n=== 测试查询: {query} ===")
            ingestor.test_retrieval(query)

        print("\n文档摄取完成！")


if __name__ == "__main__":
    main()
