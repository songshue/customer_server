#!/usr/bin/env python3
"""
知识库服务 - 文档处理与向量存储
功能：文档加载、切分、向量化、存入Qdrant
"""
import os
import sys
import re
import json
import uuid
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from langchain_community.document_loaders import (
    PyPDFLoader, 
    TextLoader, 
    Docx2txtLoader,
    UnstructuredCSVLoader,
    UnstructuredMarkdownLoader
)
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    MarkdownHeaderTextSplitter
)
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.documents import Document
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, 
    VectorParams, 
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DocumentMetadata:
    """文档元数据"""
    source: str
    file_type: str
    file_path: str
    section: str = ""
    headers: List[str] = field(default_factory=list)
    chunk_index: int = 0
    total_chunks: int = 1
    processed_at: str = field(default_factory=lambda: datetime.now().isoformat())

class DocumentProcessor:
    """文档处理器 - 支持多种格式文档加载和切分"""
    
    SUPPORTED_FORMATS = {
        ".pdf": PyPDFLoader,
        ".txt": TextLoader,
        ".docx": Docx2txtLoader,
        ".csv": UnstructuredCSVLoader,
        ".md": UnstructuredMarkdownLoader
    }
    
    MARKDOWN_HEADERS = [
        ("#", "Header1"),
        ("##", "Header2"),
        ("###", "Header3"),
        ("####", "Header4")
    ]
    
    def __init__(self, knowledge_dir: str = "knowledge", chunk_size: int = 500, chunk_overlap: int = 50):
        """
        初始化文档处理器
        
        Args:
            knowledge_dir: 知识文档目录
            chunk_size: 文本切分块大小
            chunk_overlap: 切分块重叠大小
        """
        self.knowledge_dir = Path(knowledge_dir)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embeddings = None
        
        if not self.knowledge_dir.exists():
            self.knowledge_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"创建知识库目录: {self.knowledge_dir}")
        
        api_key = os.getenv("BAILIAN_API_KEY")
        if api_key:
            print("向量模型key")
            self.embeddings = DashScopeEmbeddings(
                dashscope_api_key=api_key,
                model="text-embedding-v2"
            )
        else:
            logger.warning("未找到BAILIAN_API_KEY环境变量，将使用模拟嵌入")
    
    def clean_text(self, text: str) -> str:
        """
        清洗文本：移除HTML标签、统一换行
        
        Args:
            text: 原始文本
            
        Returns:
            清洗后的文本
        """
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()
        return text
    
    def load_document(self, file_path: Path) -> List[Document]:
        """
        加载单个文档
        
        Args:
            file_path: 文件路径
            
        Returns:
            加载的文档列表
            
        Raises:
            Exception: 加载文档失败时抛出异常
        """
        if file_path.suffix not in self.SUPPORTED_FORMATS:
            logger.warning(f"不支持的文件格式: {file_path.suffix}")
            return []
        
        try:
            logger.info(f"正在加载文档: {file_path.name}")
            
            if file_path.suffix == ".csv":
                # CSV文件处理已单独实现异常处理，直接返回
                return self.load_csv_document(file_path)
            
            loader_class = self.SUPPORTED_FORMATS[file_path.suffix]
            
            if file_path.suffix == ".pdf":
                loader = loader_class(str(file_path))
            elif file_path.suffix == ".txt":
                loader = loader_class(str(file_path), encoding='utf-8')
            elif file_path.suffix in [".docx", ".md"]:
                loader = loader_class(str(file_path))
            else:
                loader = loader_class(str(file_path))
            
            docs = loader.load()
            
            for doc in docs:
                doc.metadata["source"] = file_path.name
                doc.metadata["file_type"] = file_path.suffix
                doc.metadata["file_path"] = str(file_path)
                doc.page_content = self.clean_text(doc.page_content)
            
            logger.info(f"成功加载 {len(docs)} 个文档片段")
            return docs
            
        except Exception as e:
            logger.error(f"加载文档 {file_path.name} 时出错: {e}")
            # 抛出异常而不是返回空列表，确保错误能被上层捕获
            raise
    
    def load_csv_document(self, file_path: Path) -> List[Document]:
        """
        加载CSV文档，每行格式化为类似MD的key-value格式
        
        Args:
            file_path: CSV文件路径
            
        Returns:
            格式化的文档列表
        """
        import csv
        import chardet
        docs = []
        
        try:
            # 尝试多种编码格式
            encodings = ['utf-8', 'gbk', 'gb2312', 'utf-8-sig', 'latin1']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        reader = csv.DictReader(f)
                        columns = reader.fieldnames or []
                        
                        for row_index, row in enumerate(reader):
                            if not any(row.values()):
                                continue
                            
                            content_parts = []
                            for col in columns:
                                value = row.get(col, "").strip()
                                if value:
                                    content_parts.append(f"- **{col}**: {value}")
                            
                            if content_parts:
                                content = "## 商品信息\n\n" + "\n".join(content_parts)
                                
                                doc = Document(
                                    page_content=content,
                                    metadata={
                                        "source": file_path.name,
                                        "file_type": ".csv",
                                        "file_path": str(file_path),
                                        "row_index": row_index,
                                        "columns": columns,
                                        "chunk_type": "csv_row"
                                    }
                                )
                                docs.append(doc)
                    
                    logger.info(f"成功加载CSV文档 {file_path.name}，共 {len(docs)} 行，使用编码: {encoding}")
                    return docs
                    
                except UnicodeDecodeError:
                    continue
            
            # 自动检测编码
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                detection = chardet.detect(raw_data)
                detected_encoding = detection.get('encoding', 'utf-8')
                
            with open(file_path, 'r', encoding=detected_encoding) as f:
                reader = csv.DictReader(f)
                columns = reader.fieldnames or []
                
                for row_index, row in enumerate(reader):
                    if not any(row.values()):
                        continue
                    
                    content_parts = []
                    for col in columns:
                        value = row.get(col, "").strip()
                        if value:
                            content_parts.append(f"- **{col}**: {value}")
                    
                    if content_parts:
                        content = "## 商品信息\n\n" + "\n".join(content_parts)
                        
                        doc = Document(
                            page_content=content,
                            metadata={
                                "source": file_path.name,
                                "file_type": ".csv",
                                "file_path": str(file_path),
                                "row_index": row_index,
                                "columns": columns,
                                "chunk_type": "csv_row"
                            }
                        )
                        docs.append(doc)
            
            logger.info(f"成功加载CSV文档 {file_path.name}，共 {len(docs)} 行，自动检测编码: {detected_encoding}")
            return docs
            
        except Exception as e:
            logger.error(f"加载CSV文档 {file_path.name} 时出错: {e}")
            # 抛出异常而不是返回空列表，确保错误能被上层捕获
            raise
    
    def split_markdown_by_headers(self, documents: List[Document]) -> List[Document]:
        """
        使用MarkdownHeaderTextSplitter按标题层级切分Markdown文档
        
        Args:
            documents: Markdown文档列表
            
        Returns:
            按标题切分后的文档列表
        """
        markdown_docs = [doc for doc in documents if doc.metadata.get("file_type") == ".md"]
        non_markdown_docs = [doc for doc in documents if doc.metadata.get("file_type") != ".md"]
        
        if not markdown_docs:
            return non_markdown_docs
        
        header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.MARKDOWN_HEADERS
        )
        
        split_docs = []
        for doc in markdown_docs:
            try:
                if doc.page_content.strip():
                    splits = header_splitter.split_text(doc.page_content)
                    for i, split in enumerate(splits):
                        split.metadata = doc.metadata.copy()
                        if "headers" not in split.metadata:
                            split.metadata["headers"] = []
                        section = ""
                        for header_level, header_name in self.MARKDOWN_HEADERS:
                            if any(h[1] == header_name for h in split.metadata.get("headers", [])):
                                break
                        split.metadata["chunk_index"] = i
                        split.metadata["total_chunks"] = len(splits)
                        split.metadata["section"] = section
                        split_docs.append(split)
            except Exception as e:
                logger.error(f"切分Markdown文档时出错: {e}")
                split_docs.append(doc)
        
        split_docs.extend(non_markdown_docs)
        return split_docs
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        切分文档
        
        Args:
            documents: 文档列表
            
        Returns:
            切分后的文档列表
        """
        if not documents:
            return []
        
        markdown_docs = [doc for doc in documents if doc.metadata.get("file_type") == ".md"]
        other_docs = [doc for doc in documents if doc.metadata.get("file_type") != ".md"]
        
        split_docs = []
        
        if markdown_docs:
            split_docs.extend(self.split_markdown_by_headers(markdown_docs))
        
        if other_docs:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                length_function=len,
                separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""]
            )
            split_docs.extend(text_splitter.split_documents(other_docs))
        
        for i, doc in enumerate(split_docs):
            doc.metadata["chunk_index"] = i
            doc.metadata["total_chunks"] = len(split_docs)
            doc.metadata["processed_at"] = datetime.now().isoformat()
        
        logger.info(f"文档切分为 {len(split_docs)} 个片段")
        return split_docs
    
    def load_all_documents(self) -> List[Document]:
        """加载知识库目录中的所有文档"""
        documents = []
        for file_path in self.knowledge_dir.iterdir():
            if file_path.is_file() and file_path.suffix in self.SUPPORTED_FORMATS:
                docs = self.load_document(file_path)
                documents.extend(docs)
        return documents
    
    def process_knowledge_base(self) -> List[Document]:
        """
        处理整个知识库
        
        Returns:
            处理后的文档列表
        """
        documents = self.load_all_documents()
        split_docs = self.split_documents(documents)
        return split_docs

class QdrantVectorStore:
    """Qdrant向量存储管理"""
    
    def __init__(
        self, 
        collection_name: str = "customer_policy",
        vector_size: int = 1536,
        host: str = "localhost",
        port: int = 6333,
        max_retries: int = 3
    ):
        """
        初始化Qdrant向量存储
        
        Args:
            collection_name: 集合名称
            vector_size: 向量维度
            host: Qdrant服务器地址
            port: Qdrant端口
            max_retries: 最大重试次数
        """
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.host = host
        self.port = port
        self.max_retries = max_retries
        self.client = None
        self.connected = False
        self.connect_error = None
        
        # 尝试连接Qdrant
        self._connect()
        
    def _connect(self):
        """尝试连接到Qdrant服务器"""
        for attempt in range(self.max_retries):
            try:
                logger.info(f"尝试连接到Qdrant服务器 (尝试 {attempt+1}/{self.max_retries}): {self.host}:{self.port}")
                self.client = QdrantClient(host=self.host, port=self.port, timeout=5.0)
                # 验证连接
                self.client.get_collections()
                self.connected = True
                self.connect_error = None
                logger.info(f"成功连接到Qdrant服务器: {self.host}:{self.port}")
                # 确保集合存在
                self._ensure_collection()
                return
            except Exception as e:
                logger.warning(f"连接到Qdrant服务器失败 (尝试 {attempt+1}/{self.max_retries}): {e}")
                self.connect_error = str(e)
                self.connected = False
                if attempt < self.max_retries - 1:
                    import time
                    time.sleep(1)  # 等待1秒后重试
        
        logger.error(f"无法连接到Qdrant服务器: {self.host}:{self.port}")
        logger.error(f"最后错误: {self.connect_error}")
    
    def _ensure_connection(self) -> bool:
        """确保与Qdrant服务器的连接正常
        
        Returns:
            bool: 连接是否正常
        """
        if not self.connected:
            logger.error("未连接到Qdrant服务器")
            logger.error(f"连接错误: {self.connect_error}")
            return False
        return True
    
    def _ensure_collection(self):
        """确保集合存在"""
        if not self._ensure_connection():
            return
            
        try:
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"创建集合: {self.collection_name}")
        except Exception as e:
            logger.error(f"检查/创建集合失败: {e}")
    
    def add_documents(self, documents: List[Document], embeddings, batch_size: int = 100):
        """
        添加文档到向量存储
        
        Args:
            documents: 文档列表
            embeddings: 嵌入模型
            batch_size: 批量处理大小
        """
        if not self._ensure_connection():
            return []
            
        if not documents:
            logger.warning("没有文档需要添加")
            return []
        
        points = []
        for i, doc in enumerate(documents):
            try:
                vector = embeddings.embed_query(doc.page_content)
                point = PointStruct(
                    id=str(uuid.uuid4()),
                    vector=vector,
                    payload={
                        "page_content": doc.page_content,
                        "source": doc.metadata.get("source", ""),
                        "file_type": doc.metadata.get("file_type", ""),
                        "section": doc.metadata.get("section", ""),
                        "headers": doc.metadata.get("headers", []),
                        "chunk_index": doc.metadata.get("chunk_index", 0),
                        "total_chunks": doc.metadata.get("total_chunks", 1),
                        "processed_at": doc.metadata.get("processed_at", "")
                    }
                )
                points.append(point)
                
                if len(points) >= batch_size:
                    self.client.upsert(
                        collection_name=self.collection_name,
                        points=points
                    )
                    points = []
                    
            except Exception as e:
                logger.error(f"处理文档片段 {i} 时出错: {e}")
        
        if points:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
        
        logger.info(f"成功添加 {len(documents)} 个文档片段到 {self.collection_name}")
    
    def search(
        self, 
        query: str, 
        embeddings, 
        limit: int = 5,
        filter_source: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索相关文档
        
        Args:
            query: 查询文本
            embeddings: 嵌入模型
            limit: 返回结果数量
            filter_source: 过滤源文件
            
        Returns:
            搜索结果列表
        """
        if not self._ensure_connection():
            return []
            
        query_vector = embeddings.embed_query(query)
        
        filter_condition = None
        if filter_source:
            filter_condition = Filter(
                must=[
                    FieldCondition(key="source", match=MatchValue(value=filter_source))
                ]
            )
        
        hits = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit,
            query_filter=filter_condition
        )
        
        return [
            {
                "content": hit.payload.get("page_content", ""),
                "source": hit.payload.get("source", ""),
                "section": hit.payload.get("section", ""),
                "score": hit.score
            }
            for hit in hits
        ]

    def search_knowledge(self, query: str, limit: int = 5, filter_source: str = None) -> List[Dict[str, Any]]:
        """
        搜索知识库（与KnowledgeBasePipeline接口兼容）
        
        Args:
            query: 查询文本
            limit: 返回结果数量
            filter_source: 过滤源文件
            
        Returns:
            搜索结果列表
        """
        if not self._ensure_connection():
            return []
        
        try:
            from langchain_community.embeddings import DashScopeEmbeddings
            import os
            
            # 初始化嵌入模型
            api_key = (os.getenv("DASHSCOPE_API_KEY") or 
                      os.getenv("BAILIAN_API_KEY") or 
                      os.getenv("OPENAI_API_KEY"))
            
            if not api_key:
                logger.error("未找到API密钥（DASHSCOPE_API_KEY/BAILIAN_API_KEY/OPENAI_API_KEY）")
                return []
            
            embeddings = DashScopeEmbeddings(
                model="text-embedding-v2",
                dashscope_api_key=api_key
            )
            
            return self.search(query, embeddings, limit, filter_source)
        except Exception as e:
            logger.error(f"知识库搜索失败: {e}")
            return []
    

    
    def delete_by_source(self, source: str):
        """
        删除指定源的所有文档
        
        Args:
            source: 源文件名
        """
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(key="source", match=MatchValue(value=source))
                ]
            )
        )
        logger.info(f"删除源文件 {source} 的文档")
    
    def delete_collection(self):
        """
        删除整个集合"""
        if not self._ensure_connection():
            return False
            
        try:
            self.client.delete_collection(self.collection_name)
            logger.info(f"删除集合: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"删除集合失败: {e}")
            return False
    
    def delete_chunk(self, point_id: str):
        """
        删除单个chunk
        
        Args:
            point_id: chunk ID
            
        Returns:
            是否成功
        """
        if not self._ensure_connection():
            return False
            
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[point_id]
            )
            logger.info(f"删除 chunk: {point_id}")
            return True
        except Exception as e:
            logger.error(f"删除 chunk 失败: {e}")
            return False
    
    def update_chunk(self, point_id: str, new_content: str, new_metadata: Dict[str, Any] = None, embeddings = None):
        """
        更新单个chunk
        
        Args:
            point_id: chunk ID
            new_content: 新的内容
            new_metadata: 新的元数据
            embeddings: 嵌入模型
            
        Returns:
            是否成功
        """
        try:
            payload = {"page_content": new_content}
            if new_metadata:
                payload.update(new_metadata)
            
            points = [PointStruct(
                id=point_id,
                vector=[],
                payload=payload
            )]
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            logger.info(f"更新 chunk: {point_id}")
            return True
        except Exception as e:
            logger.error(f"更新 chunk 失败: {e}")
            return False
    
    def add_chunk(self, content: str, metadata: Dict[str, Any], embeddings, point_id: str = None):
        """
        添加单个chunk
        
        Args:
            content: 内容
            metadata: 元数据
            embeddings: 嵌入模型
            point_id: 指定ID，不指定则自动生成
            
        Returns:
            生成的chunk ID
        """
        try:
            vector = embeddings.embed_query(content)
            pid = point_id or str(uuid.uuid4())
            
            point = PointStruct(
                id=pid,
                vector=vector,
                payload={
                    "page_content": content,
                    **metadata
                }
            )
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            logger.info(f"添加 chunk: {pid}")
            return pid
        except Exception as e:
            logger.error(f"添加 chunk 失败: {e}")
            return None
    
    def get_chunk(self, point_id: str) -> Dict[str, Any]:
        """
        获取单个chunk
        
        Args:
            point_id: chunk ID
            
        Returns:
            chunk信息
        """
        try:
            point = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[point_id]
            )
            if point:
                return {
                    "id": point[0].id,
                    "payload": point[0].payload
                }
            return None
        except Exception as e:
            logger.error(f"获取 chunk 失败: {e}")
            return None
    
    def rename_collection(self, new_name: str):
        """
        重命名集合
        
        Args:
            new_name: 新名称
            
        Returns:
            是否成功
        """
        try:
            self.client.update_collection(
                collection_name=self.collection_name,
                new_collection_name=new_name
            )
            old_name = self.collection_name
            self.collection_name = new_name
            logger.info(f"重命名集合: {old_name} -> {new_name}")
            return True
        except Exception as e:
            logger.error(f"重命名集合失败: {e}")
            return False
    
    def get_collection_info(self) -> Dict[str, Any]:
        """获取集合信息"""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            vectors_count = getattr(collection_info, 'vectors_count', 
                          getattr(collection_info, 'points_count', 0))
            status = getattr(collection_info, 'status', 'unknown')
            return {
                "name": self.collection_name,
                "vectors_count": vectors_count,
                "status": status
            }
        except Exception as e:
            logger.error(f"获取集合信息失败: {e}")
            return {
                "name": self.collection_name,
                "vectors_count": 0,
                "status": "error"
            }

class KnowledgeBasePipeline:
    """知识库处理流水线"""
    
    def __init__(
        self, 
        knowledge_dir: str = "knowledge",
        collection_name: str = "customer_policy",
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ):
        """
        初始化知识库处理流水线
        
        Args:
            knowledge_dir: 知识库目录
            collection_name: Qdrant集合名
            qdrant_host: Qdrant服务器地址
            qdrant_port: Qdrant端口
            chunk_size: 切分块大小
            chunk_overlap: 切分块重叠
        """
        self.processor = DocumentProcessor(knowledge_dir, chunk_size, chunk_overlap)
        self.vector_store = QdrantVectorStore(
            collection_name=collection_name,
            host=qdrant_host,
            port=qdrant_port
        )
    
    def run(self, clear_existing: bool = False):
        """
        运行知识库处理流水线
        
        Args:
            clear_existing: 是否清除已有数据
            
        Returns:
            处理结果统计
        """
        logger.info("开始知识库处理流水线...")
        
        if clear_existing:
            try:
                self.vector_store.client.delete_collection(self.vector_store.collection_name)
                self.vector_store._ensure_collection()
                logger.info(f"已清除集合 {self.vector_store.collection_name} 的数据")
            except Exception as e:
                logger.error(f"清除集合数据失败: {e}")
        
        documents = self.processor.process_knowledge_base()
        
        if not documents:
            logger.warning("没有文档需要处理")
            return {"success": False, "documents_processed": 0}
        
        if not self.processor.embeddings:
            logger.error("嵌入模型未初始化，无法进行向量化")
            return {"success": False, "message": "Embeddings not initialized"}
        
        self.vector_store.add_documents(documents, self.processor.embeddings)
        
        collection_info = self.vector_store.get_collection_info()
        
        logger.info(f"知识库处理流水线完成: {collection_info}")
        
        return {
            "success": True,
            "documents_processed": len(documents),
            "collection_info": collection_info
        }
    
    def add_single_document(self, file_path: str):
        """
        添加单个文档到知识库
        
        Args:
            file_path: 文件路径
            
        Raises:
            Exception: 文档处理失败时抛出异常
        """
        path = Path(file_path)
        if not path.exists():
            logger.error(f"文件不存在: {file_path}")
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        source = path.name
        
        if self.vector_store:
            self.vector_store.delete_by_source(source)
        
        try:
            documents = self.processor.load_document(path)
            split_docs = self.processor.split_documents(documents)
            
            if split_docs and self.processor.embeddings:
                self.vector_store.add_documents(split_docs, self.processor.embeddings)
                logger.info(f"文档 {source} 处理完成")
            else:
                logger.warning(f"文档 {source} 未生成有效文档片段")
                raise ValueError(f"文档 {source} 未生成有效文档片段")
        except Exception as e:
            logger.error(f"处理文档 {source} 时出错: {e}")
            raise
    
    def search_knowledge(self, query: str, limit: int = 5, filter_source: str = None) -> List[Dict[str, Any]]:
        """
        搜索知识库
        
        Args:
            query: 查询文本
            limit: 返回结果数量
            filter_source: 过滤源文件
            
        Returns:
            搜索结果
        """
        if not self.processor.embeddings:
            logger.error("嵌入模型未初始化")
            return []
        
        return self.vector_store.search(
            query, 
            self.processor.embeddings, 
            limit=limit,
            filter_source=filter_source
        )

def create_knowledge_pipeline(
    knowledge_dir: str = "knowledge",
    collection_name: str = "customer_policy"
) -> KnowledgeBasePipeline:
    """
    创建知识库处理流水线的工厂函数
    
    Args:
        knowledge_dir: 知识库目录
        collection_name: 集合名称
        
    Returns:
        KnowledgeBasePipeline实例
    """
    return KnowledgeBasePipeline(
        knowledge_dir=knowledge_dir,
        collection_name=collection_name
    )
