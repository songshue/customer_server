#!/usr/bin/env python3
"""
多Agent协同系统 - 智能客服多Agent实现
功能：主路由Agent + 专业子Agent + Agent协同 + 流式输出

重构说明：此文件现在作为模块入口点，重新导出重构后的Agent和工具类
"""
import os
import sys
import json
import time
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
from enum import Enum
from pydantic import BaseModel

# 确保当前目录在Python路径中
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入共享类型
from .shared_types import IntentType, AgentResponse

# 重新导出重构后的模块
try:
    from .agents.intent_router import IntentRouterAgent
    from .agents.order_agent import OrderAgent
    from .agents.after_sales_agent import AfterSalesAgent
    from .agents.product_agent import ProductAgent
    from .agents.coordinator import AgentCoordinator, get_agent_coordinator
    
    from .tools.database_tool import DatabaseTool
    from .tools.redis_tool import RedisTool
    from .tools.logger_tool import LoggerTool
    from .tools.common_tool import CommonTool
    
    logger.info("多Agent系统重构成功，所有模块导入正常")
    
except ImportError as e:
    logger.error(f"导入重构后的模块失败: {e}")
    
    # 提供向后兼容的类定义，避免其他模块导入失败
    class IntentRouterAgent:
        def __init__(self, *args, **kwargs):
            raise ImportError("IntentRouterAgent未正确导入")
    
    class OrderAgent:
        def __init__(self, *args, **kwargs):
            raise ImportError("OrderAgent未正确导入")
    
    class AfterSalesAgent:
        def __init__(self, *args, **kwargs):
            raise ImportError("AfterSalesAgent未正确导入")
    
    class ProductAgent:
        def __init__(self, *args, **kwargs):
            raise ImportError("ProductAgent未正确导入")
    
    class AgentCoordinator:
        def __init__(self, *args, **kwargs):
            raise ImportError("AgentCoordinator未正确导入")
    
    def get_agent_coordinator(*args, **kwargs):
        raise ImportError("get_agent_coordinator未正确导入")
    
    class DatabaseTool:
        def __init__(self, *args, **kwargs):
            raise ImportError("DatabaseTool未正确导入")
    
    class RedisTool:
        def __init__(self, *args, **kwargs):
            raise ImportError("RedisTool未正确导入")
    
    class LoggerTool:
        def __init__(self, *args, **kwargs):
            raise ImportError("LoggerTool未正确导入")
    
    class CommonTool:
        def __init__(self, *args, **kwargs):
            raise ImportError("CommonTool未正确导入")

# 保持向后兼容的全局实例（如果有人还在使用旧的方式）
agent_coordinator = None

def get_legacy_agent_coordinator(rag_pipeline=None) -> AgentCoordinator:
    """获取全局Agent协调器实例（向后兼容）"""
    global agent_coordinator
    if agent_coordinator is None:
        agent_coordinator = get_agent_coordinator(rag_pipeline)
    return agent_coordinator

# 为了向后兼容，保留一些常用的函数
async def process_message(user_input: str, session_id: str = None) -> AgentResponse:
    """处理用户消息的主入口（向后兼容）"""
    coordinator = get_legacy_agent_coordinator()
    return await coordinator.process_message(user_input, session_id)

async def stream_response(user_input: str, session_id: str = None) -> AsyncGenerator[str, None]:
    """流式响应生成器（向后兼容）"""
    coordinator = get_legacy_agent_coordinator()
    async for chunk in coordinator.stream_response(user_input, session_id):
        yield chunk