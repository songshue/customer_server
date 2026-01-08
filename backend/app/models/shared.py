from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class IntentType(Enum):
    """用户意图类型"""
    PRESALES = "presales"
    ORDER = "order"
    LOGISTICS = "logistics"
    AFTER_SALES = "after_sales"
    RECOMMENDATION = "recommendation"
    COMPLAINT = "complaint"
    GREETING = "greeting"
    GENERAL = "general"
    UNKNOWN = "unknown"

class AgentResponse(BaseModel):
    """Agent响应数据结构"""
    success: bool
    content: str
    intent: Optional[IntentType] = None
    sources: List[Dict[str, Any]] = []
    order_info: Optional[Dict[str, Any]] = None
    product_info: Optional[Dict[str, Any]] = None
    context: Dict[str, Any] = {}
