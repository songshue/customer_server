#!/usr/bin/env python3
"""
订单Agent - 处理订单相关查询
功能：查询订单状态、订单详情、修改订单等
"""
import os
import sys
import json
import time
import asyncio
import logging
from typing import Dict, Any, Optional, List, AsyncGenerator

# 导入LLM配置
from ..llm_config import create_llm_with_custom_config
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate

# 导入工具类
from ..tools.database_tool import DatabaseTool
from ..tools.common_tool import CommonTool
from ..tools.logger_tool import LoggerTool

# 确保当前目录在Python路径中
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 导入管理器
try:
    from ...managers.mysql_manager import mysql_manager
    from ...managers.redis_manager import redis_manager
    from ...managers.logger_manager import logger_manager
except ImportError as e:
    logging.warning(f"导入管理器模块失败: {e}")
    mysql_manager = None
    redis_manager = None
    logger_manager = None

# 导入共享类型
from ..shared_types import IntentType, AgentResponse

# 配置日志
logger = logging.getLogger(__name__)

class OrderAgent:
    """订单Agent - 查询订单状态和信息"""
    
    def __init__(self, logger_tool: Optional[LoggerTool] = None, db_tool: Optional[DatabaseTool] = None, 
                 common_tool: Optional[CommonTool] = None):
        """初始化订单Agent"""
        self.logger_tool = logger_tool or LoggerTool(logger)
        self.db_tool = db_tool or DatabaseTool(mysql_manager)
        self.common_tool = common_tool or CommonTool()
        self.llm = self._init_llm()
    
    def _init_llm(self):
        """初始化LLM模型"""
        try:
            # 使用统一的LLM配置
            llm = create_llm_with_custom_config(
                temperature=0.1,
                max_tokens=1000  # 订单查询可能需要较长的输出
            )
            
            if llm:
                return llm
            else:
                logger.warning("未找到API密钥或配置，使用模拟响应")
                return None
        except Exception as e:
            logger.error(f"初始化LLM失败: {e}")
            return None
    
    async def query_order(self, order_id: str = None, user_input: str = None, session_id: str = None) -> AgentResponse:
        """查询订单信息"""
        start_time = time.time()
        
        try:
            # 记录查询开始
            if self.logger_tool:
                await self.logger_tool.log_system_event(
                    event_type="ORDER_QUERY_START",
                    message=f"开始查询订单: {order_id or '未提供订单号'}",
                    details={
                        "order_id": order_id,
                        "session_id": session_id,
                        "user_input": user_input
                    }
                )
            
            order_info = None
            
            # 如果提供了订单号，直接查询
            if order_id:
                # 验证订单号格式
                if not self.common_tool.validate_order_id(order_id):
                    processing_time = time.time() - start_time
                    return AgentResponse(
                        success=False,
                        content="订单号格式不正确，请检查后重试",
                        intent=IntentType.ORDER,
                        context={
                            "processing_time": processing_time,
                            "query_method": "invalid_format"
                        }
                    )
                
                order_info = await self.db_tool.query_order_by_id(order_id)
                
            elif user_input:
                # 从用户输入中提取订单号
                order_id = self.common_tool.extract_order_id_from_text(user_input)
                if order_id:
                    # 验证并查询订单
                    if self.common_tool.validate_order_id(order_id):
                        order_info = await self.db_tool.query_order_by_id(order_id)
            
            processing_time = time.time() - start_time
            
            # 记录查询结果
            if self.logger_tool:
                await self.logger_tool.log_system_event(
                    event_type="ORDER_QUERY_RESULT",
                    message=f"订单查询完成: {'成功' if order_info else '失败'}",
                    details={
                        "order_id": order_id,
                        "success": order_info is not None,
                        "processing_time": processing_time
                    }
                )
            
            if order_info:
                # 添加脱敏处理
                if "customer_phone" in order_info:
                    order_info["customer_phone_masked"] = self.common_tool.mask_phone_number(order_info["customer_phone"])
                
                return AgentResponse(
                    success=True,
                    content=f"已查询到订单信息：{order_info.get('product_name', '商品')}，订单状态：{order_info.get('status', '未知')}",
                    intent=IntentType.ORDER,
                    order_info=order_info,
                    context={
                        "processing_time": processing_time,
                        "query_method": "direct_query",
                        "order_id": order_id
                    }
                )
            else:
                return AgentResponse(
                    success=False,
                    content="未找到相关订单信息，请检查订单号是否正确",
                    intent=IntentType.ORDER,
                    context={
                        "processing_time": processing_time,
                        "query_method": "failed_query",
                        "order_id": order_id
                    }
                )
                
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"订单查询失败: {e}"
            logger.error(error_msg)
            
            # 记录错误
            if self.logger_tool:
                await self.logger_tool.log_system_event(
                    event_type="ORDER_QUERY_ERROR",
                    message=error_msg,
                    details={
                        "order_id": order_id,
                        "error": str(e),
                        "processing_time": processing_time
                    }
                )
            
            return AgentResponse(
                success=False,
                content="抱歉，订单查询服务暂时不可用，请稍后重试。",
                intent=IntentType.ORDER,
                context={
                    "error": str(e),
                    "processing_time": processing_time
                }
            )

    async def stream_query_order(self, order_id: str = None, user_input: str = None, session_id: str = None) -> AsyncGenerator[str, None]:
        """流式查询订单信息"""
        start_time = time.time()
        
        try:
            # 记录查询开始
            if self.logger_tool:
                await self.logger_tool.log_system_event(
                    event_type="ORDER_STREAM_START",
                    message=f"开始流式查询订单: {order_id or '未提供订单号'}",
                    details={
                        "order_id": order_id,
                        "session_id": session_id,
                        "user_input": user_input
                    }
                )
            
            # 发送准备信息
            yield "我正在为您查询订单信息..."
            
            order_info = None
            
            # 如果提供了订单号，直接查询
            if order_id:
                # 验证订单号格式
                if not self.common_tool.validate_order_id(order_id):
                    yield "订单号格式不正确，请检查后重试"
                    return
                
                yield "正在验证订单号..."
                order_info = await self.db_tool.query_order_by_id(order_id)
                
            elif user_input:
                # 从用户输入中提取订单号
                yield "正在从您的输入中提取订单号..."
                order_id = self.common_tool.extract_order_id_from_text(user_input)
                if order_id:
                    # 验证并查询订单
                    if self.common_tool.validate_order_id(order_id):
                        yield f"找到订单号 {order_id}，正在查询详细信息..."
                        order_info = await self.db_tool.query_order_by_id(order_id)
            
            processing_time = time.time() - start_time
            
            if order_info:
                # 添加脱敏处理
                if "customer_phone" in order_info:
                    order_info["customer_phone_masked"] = self.common_tool.mask_phone_number(order_info["customer_phone"])
                
                # 生成流式回答
                yield "已查询到订单信息，正在为您详细说明..."
                
                # 流式生成订单详情
                order_details = self._generate_order_details_response(order_info)
                for char in order_details:
                    yield char
                    # await asyncio.sleep(0.01)  # 控制输出速度
                
                # 记录查询结果
                if self.logger_tool:
                    await self.logger_tool.log_system_event(
                        event_type="ORDER_STREAM_COMPLETE",
                        message=f"订单流式查询完成: 成功",
                        details={
                            "order_id": order_id,
                            "success": True,
                            "processing_time": processing_time
                        }
                    )
            else:
                yield "未找到相关订单信息，请检查订单号是否正确"
                
                # 记录查询结果
                if self.logger_tool:
                    await self.logger_tool.log_system_event(
                        event_type="ORDER_STREAM_COMPLETE",
                        message=f"订单流式查询完成: 失败",
                        details={
                            "order_id": order_id,
                            "success": False,
                            "processing_time": processing_time
                        }
                    )
                
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"订单流式查询失败: {e}"
            logger.error(error_msg)
            
            # 记录错误
            if self.logger_tool:
                await self.logger_tool.log_system_event(
                    event_type="ORDER_STREAM_ERROR",
                    message=error_msg,
                    details={
                        "order_id": order_id,
                        "error": str(e),
                        "processing_time": processing_time
                    }
                )
            
            yield "抱歉，订单查询服务暂时不可用，请稍后重试。"

    def _generate_order_details_response(self, order_info: Dict[str, Any]) -> str:
        """生成订单详情回答"""
        response_parts = []
        
        response_parts.append(f"📦 订单详情：")
        response_parts.append(f"• 订单号：{order_info.get('order_id', 'N/A')}")
        response_parts.append(f"• 商品名称：{order_info.get('product_name', 'N/A')}")
        response_parts.append(f"• 订单状态：{order_info.get('status', 'N/A')}")
        response_parts.append(f"• 下单时间：{order_info.get('created_at', 'N/A')}")
        response_parts.append(f"• 支付状态：{order_info.get('payment_status', 'N/A')}")
        response_parts.append(f"• 收货地址：{order_info.get('shipping_address', 'N/A')}")
        
        if order_info.get('customer_phone_masked'):
            response_parts.append(f"• 联系电话：{order_info['customer_phone_masked']}")
        
        response_parts.append(f"\n如需了解更多信息，请告诉我您的具体需求。")
        
        return '\n'.join(response_parts)
