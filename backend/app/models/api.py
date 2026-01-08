from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str

class SessionCreateRequest(BaseModel):
    """创建会话请求模型"""
    title: Optional[str] = None

class SessionResponse(BaseModel):
    """会话响应模型"""
    session_id: str
    title: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    message_count: int = 0
    status: str = "active"
    last_message: Optional[str] = None

class SessionListResponse(BaseModel):
    """会话列表响应模型"""
    sessions: List[SessionResponse]
    total: int

class SessionRenameRequest(BaseModel):
    """会话重命名请求模型"""
    title: str

class SearchRequest(BaseModel):
    """搜索请求模型"""
    query: str
    collection_name: str = "customer_policy"
    limit: int = 5
    filter_source: Optional[str] = None

class SearchResponse(BaseModel):
    """搜索响应模型"""
    success: bool
    results: List[Dict[str, Any]]
    query: str

class UploadResponse(BaseModel):
    """上传响应模型"""
    success: bool
    message: str
    filename: str
    collection_name: str
    chunks_processed: int = 0

class CollectionInfoResponse(BaseModel):
    """集合信息响应模型"""
    success: bool
    info: Dict[str, Any]
