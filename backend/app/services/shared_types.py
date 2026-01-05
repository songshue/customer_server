#!/usr/bin/env python3
"""
共享类型定义 - 多Agent系统公共类型
功能：定义IntentType和AgentResponse等公共类型
"""
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

class IntentType(Enum):
    """用户意图类型"""
    PRESALES = "presales"        # 售前咨询
    ORDER = "order"             # 订单相关
    AFTER_SALES = "after_sales" # 售后问题
    RECOMMENDATION = "recommendation" # 商品推荐
    COMPLAINT = "complaint"     # 投诉建议
    GREETING = "greeting"     # 问候语
    GENERAL = "general"         # 通用意图（缓存命中场景）
    UNKNOWN = "unknown"         # 未知意图

class AgentResponse(BaseModel):
    """Agent响应数据结构"""
    success: bool
    content: str
    intent: Optional[IntentType] = None
    sources: List[Dict[str, Any]] = []
    order_info: Optional[Dict[str, Any]] = None
    product_info: Optional[Dict[str, Any]] = None
    context: Dict[str, Any] = {}