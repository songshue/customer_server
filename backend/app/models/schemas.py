from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class ChatMessage(BaseModel):
    """聊天消息模型"""
    message: str
    session_id: str
    user_id: Optional[str] = None
    timestamp: Optional[datetime] = None

class ChatResponse(BaseModel):
    """聊天响应模型"""
    response: str
    session_id: str
    timestamp: datetime
    message_type: str = "chat"

class UserLogin(BaseModel):
    """用户登录模型"""
    username: str
    password: Optional[str] = None

class UserToken(BaseModel):
    """用户令牌模型"""
    access_token: str
    username: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None

class RefreshTokenRequest(BaseModel):
    """刷新令牌请求模型"""
    refresh_token: str

class LogoutRequest(BaseModel):
    """登出请求模型"""
    refresh_token: Optional[str] = None

class SessionInfo(BaseModel):
    """会话信息模型"""
    session_id: str
    user_id: Optional[str] = None
    created_at: datetime
    last_activity: datetime
    status: str = "active"

class WebSocketMessage(BaseModel):
    """WebSocket消息模型"""
    type: str
    data: Dict[str, Any]
    timestamp: Optional[datetime] = None

    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now()
        super().__init__(**data)
