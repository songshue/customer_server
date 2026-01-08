#!/usr/bin/env python3
"""
Agent协调器 - 管理多Agent协同
功能：统一消息处理、Agent调度、统计管理、流式响应
"""
import os
import sys
import json
import time
import logging
import random
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator

from langchain_core.prompts import ChatPromptTemplate

# 导入工具类
from ..tools.logger_tool import LoggerTool
from ..tools.redis_tool import RedisTool

# 导入各个Agent
from .intent_router import IntentRouterAgent
from .order_agent import OrderAgent
from .after_sales_agent import AfterSalesAgent
from .product_agent import ProductAgent

# 导入共享类型
from app.models import IntentType, AgentResponse

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

# 导入数据库和通用工具
from ..tools.database_tool import DatabaseTool
from ..tools.common_tool import CommonTool

# 配置日志
logger = logging.getLogger(__name__)

class AgentCoordinator:
    """Agent协调器 - 管理多Agent协同"""
    
    def __init__(self, rag_pipeline=None, logger_tool: Optional[LoggerTool] = None, 
                 redis_tool: Optional[RedisTool] = None):
        """初始化Agent协调器"""
        # 初始化工具类
        self.logger_tool = logger_tool or LoggerTool(logger)
        self.redis_tool = redis_tool or RedisTool(redis_manager)
        self.db_tool = DatabaseTool(mysql_manager)
        self.common_tool = CommonTool()
        
        # 初始化各个Agent，注入工具依赖
        self.intent_router = IntentRouterAgent(self.logger_tool)
        self.order_agent = OrderAgent(self.logger_tool, self.db_tool, self.common_tool)
        self.after_sales_agent = AfterSalesAgent(rag_pipeline, self.logger_tool, self.redis_tool)
        self.product_agent = ProductAgent(rag_pipeline, self.logger_tool, self.redis_tool)
        
        self.rag_pipeline = rag_pipeline
        
        # Agent调用统计
        self.agent_stats = {
            "intent_router": {"calls": 0, "success_rate": 0.0, "avg_processing_time": 0.0},
            "order_agent": {"calls": 0, "success_rate": 0.0, "avg_processing_time": 0.0},
            "after_sales_agent": {"calls": 0, "success_rate": 0.0, "avg_processing_time": 0.0},
            "product_agent": {"calls": 0, "success_rate": 0.0, "avg_processing_time": 0.0}
        }
    
    async def process_message(self, user_input: str, session_id: str = None) -> AgentResponse:
        """处理用户消息的主入口"""
        start_time = time.time()
        
        try:
            # 记录消息处理开始
            await self.logger_tool.log_system_event(
                event_type="MESSAGE_PROCESS_START",
                message=f"开始处理用户消息: {user_input[:50]}...",
                details={
                    "session_id": session_id,
                    "user_input": user_input
                }
            )
            
            # 0. 优先检查缓存命中（如果Redis管理器可用）
            if redis_manager:
                try:
                    cached_response = await redis_manager.get_cached_response(user_input)
                    if cached_response:
                        logger.info(f"AgentCoordinator命中缓存，直接返回: {user_input[:30]}...")
                        print(f"AgentCoordinator命中缓存，直接返回: {user_input[:30]}...")
                        
                        # 返回缓存的回复
                        return AgentResponse(
                            content=cached_response["response"],
                            success=True,
                            intent=IntentType.GENERAL,
                            sources=[],
                            context={
                                "cache_hit": True,
                                "cached_time": cached_response["timestamp"],
                                "processing_time": time.time() - start_time
                            }
                        )
                    else:
                        logger.debug(f"AgentCoordinator缓存未命中，继续处理: {user_input[:30]}...")
                        print(f"AgentCoordinator缓存未命中，继续处理: {user_input[:30]}...")
                except Exception as cache_error:
                    error_msg = str(cache_error) if cache_error else "未知异常"
                    logger.warning(f"缓存检查失败，继续正常处理: {error_msg}")
            
            # 1. 意图路由
            logger.info("开始意图路由...")
            route_result = await self.intent_router.route(user_input)
            self._update_agent_stats("intent_router", route_result.success, route_result.context.get("processing_time", 0))
            
            if not route_result.success:
                return route_result
            
            intent = route_result.intent
            extracted_info = route_result.context.get("extracted_info", {})
            
            # 2. 根据意图调用相应的Agent
            agent_result = None
            
            if intent == IntentType.ORDER:
                order_id = extracted_info.get("order_id")
                logger.info(f"调用订单Agent，订单号: {order_id}")
                agent_result = await self.order_agent.query_order(order_id, user_input, session_id)
                self._update_agent_stats("order_agent", agent_result.success, agent_result.context.get("processing_time", 0))
                
            elif intent == IntentType.LOGISTICS:
                tracking_number = extracted_info.get("tracking_number")
                order_id = extracted_info.get("order_id")
                logger.info(f"调用物流查询，订单号: {order_id}, 快递单号: {tracking_number}")
                agent_result = await self.order_agent.query_logistics(tracking_number, order_id)
                self._update_agent_stats("order_agent", agent_result.success, agent_result.context.get("processing_time", 0))
                
            elif intent == IntentType.AFTER_SALES:
                order_id = extracted_info.get("order_id")
                order_info = None
                
                if order_id:
                    order_result = await self.order_agent.query_order(order_id, session_id=session_id)
                    if order_result.success:
                        order_info = order_result.order_info
                
                logger.info("调用售后Agent完整回答方法...")
                agent_result = await self.after_sales_agent.handle_after_sales(user_input, order_info, session_id)
                self._update_agent_stats("after_sales_agent", agent_result.success, agent_result.context.get("processing_time", 0))
                
            elif intent == IntentType.PRESALES:
                logger.info("调用商品Agent完整回答方法...")
                agent_result = await self.product_agent.query_product(user_input, session_id)
                self._update_agent_stats("product_agent", agent_result.success, agent_result.context.get("processing_time", 0))
                
            elif intent == IntentType.GREETING:
                logger.info("处理问候语完整回答...")
                agent_result = await self._handle_greeting(user_input)
                
            elif intent == IntentType.UNKNOWN:
                logger.info("未知意图，使用通用完整回答...")
                agent_result = await self._handle_unknown_intent(user_input)
                
            else:
                logger.info(f"其他意图类型完整回答: {intent.value}")
                agent_result = await self._handle_general_intent(intent, user_input)
            
            # 3. 添加路由信息到结果中
            if agent_result:
                agent_result.context["intent_routing"] = route_result.context
                agent_result.context["total_processing_time"] = time.time() - start_time
                
                # 记录用户交互
                await self.logger_tool.log_user_interaction(
                    user_id="unknown",  # 这里应该从会话中获取真实用户ID
                    session_id=session_id or "default",
                    user_input=user_input,
                    agent_response=agent_result.content,
                    metadata={
                        "intent": intent.value,
                        "success": agent_result.success,
                        "processing_time": agent_result.context.get("total_processing_time", 0)
                    }
                )
                
                # 4. 多Agent场景下的热门问题缓存逻辑
                await self._cache_hot_questions(user_input, agent_result.content, intent)
            
            return agent_result
            
        except Exception as e:
            total_time = time.time() - start_time
            error_msg = f"消息处理失败: {e}"
            logger.error(error_msg)
            
            # 记录错误
            await self.logger_tool.log_system_event(
                event_type="MESSAGE_PROCESS_ERROR",
                message=error_msg,
                details={
                    "session_id": session_id,
                    "user_input": user_input[:100],
                    "error": str(e),
                    "processing_time": total_time
                }
            )
            
            return AgentResponse(
                success=False,
                content="抱歉，系统处理您的消息时出现错误，请稍后重试或联系人工客服。",
                intent=IntentType.UNKNOWN,
                context={
                    "error": str(e),
                    "total_processing_time": total_time
                }
            )
    
    async def _handle_greeting(self, user_input: str) -> AgentResponse:
        """处理问候语"""
        greetings = [
            "您好！欢迎使用我们的智能客服系统，我是AI助手，很高兴为您服务！请问有什么可以帮助您的吗？",
            "Hello！很高兴为您提供帮助。请告诉我您遇到了什么问题，我会尽力为您解决。",
            "您好！我是您的专属客服助手，请输入您的问题，我将为您提供专业服务。"
        ]
        
        content = random.choice(greetings)
        
        return AgentResponse(
            success=True,
            content=content,
            intent=IntentType.GREETING,
            context={"response_type": "greeting"}
        )
    
    async def _handle_unknown_intent(self, user_input: str) -> AgentResponse:
        """处理未知意图"""
        content = """抱歉，我没有完全理解您的问题。

我可以帮助您处理以下类型的问题：
• 商品咨询和推荐
• 订单查询和状态跟踪
• 售后服务和退换货
• 投诉建议和意见反馈

请重新描述您的问题，我会尽力为您提供帮助！"""
        
        return AgentResponse(
            success=True,
            content=content,
            intent=IntentType.UNKNOWN,
            context={"response_type": "help_suggestion"}
        )
    
    async def _handle_general_intent(self, intent: IntentType, user_input: str) -> AgentResponse:
        """处理通用意图"""
        if intent == IntentType.RECOMMENDATION:
            content = "我来为您推荐合适的产品。请告诉我您的具体需求，比如预算范围、使用场景、品牌偏好等，我会为您提供个性化的产品推荐。"
        elif intent == IntentType.COMPLAINT:
            content = "非常抱歉给您带来不好的体验。我会将您的问题和建议认真记录并反馈给相关部门。如果需要人工客服介入，我也可以为您转接。"
        else:
            content = "我正在学习中，请提供更多详细信息，我会尽力帮助您解决问题。"
        
        return AgentResponse(
            success=True,
            content=content,
            intent=intent,
            context={"response_type": "general"}
        )
    
    def _update_agent_stats(self, agent_name: str, success: bool, processing_time: float):
        """更新Agent统计信息"""
        if agent_name in self.agent_stats:
            stats = self.agent_stats[agent_name]
            stats["calls"] += 1
            
            # 计算成功率
            if stats["calls"] > 0:
                success_count = int(stats["success_rate"] * (stats["calls"] - 1))
                if success:
                    success_count += 1
                stats["success_rate"] = success_count / stats["calls"]
            
            # 更新平均处理时间
            if stats["calls"] == 1:
                stats["avg_processing_time"] = processing_time
            else:
                # 简单的移动平均
                stats["avg_processing_time"] = (stats["avg_processing_time"] * (stats["calls"] - 1) + processing_time) / stats["calls"]
    
    def get_agent_stats(self) -> Dict[str, Any]:
        """获取Agent统计信息"""
        return self.agent_stats.copy()
    
    async def stream_response(self, user_input: str, session_id: str = None) -> AsyncGenerator[str, None]:
        """流式响应生成器 - 真正的端到端流式输出"""
        try:
            # 记录流式响应开始
            await self.logger_tool.log_system_event(
                event_type="STREAM_RESPONSE_START",
                message=f"用户 {session_id} 开始流式响应",
                details={
                    "session_id": session_id,
                    "user_input": user_input[:100]
                }
            )
            
            # 0. 优先检查缓存命中 - 如果命中缓存，直接返回完整答案（不流式输出）
            if redis_manager:
                try:
                    cached_response = await redis_manager.get_cached_response(user_input)
                    if cached_response:
                        logger.info(f"AgentCoordinator命中缓存，直接返回完整答案: {user_input[:30]}...")
                        print(f"AgentCoordinator命中缓存，直接返回完整答案: {user_input[:30]}...")
                        
                        # 直接返回缓存的完整答案，不需要流式输出
                        yield cached_response["response"]
                        return
                    else:
                        logger.debug(f"AgentCoordinator缓存未命中，继续流式处理: {user_input[:30]}...")
                        print(f"AgentCoordinator缓存未命中，继续流式处理: {user_input[:30]}...")
                except Exception as cache_error:
                    error_msg = str(cache_error) if cache_error else "未知异常"
                    logger.warning(f"缓存检查失败，继续正常处理: {error_msg}")
            
            # 1. 意图路由
            route_result = await self.intent_router.route(user_input)
            
            if not route_result.success:
                yield route_result.content
                return
            
            intent = route_result.intent
            extracted_info = route_result.context.get("extracted_info", {})
            
            # 2. 根据意图调用相应的Agent流式方法 - 端到端流式传递
            if intent == IntentType.ORDER:
                order_id = extracted_info.get("order_id")
                # 直接传递子agent的流式输出
                async for chunk in self.order_agent.stream_query_order(order_id, user_input, session_id):
                    yield chunk
                    
            elif intent == IntentType.AFTER_SALES:
                order_id = extracted_info.get("order_id")
                order_info = None
                
                if order_id:
                    order_result = await self.order_agent.query_order(order_id, session_id=session_id)
                    if order_result.success:
                        order_info = order_result.order_info
                
                # 直接传递after_sales_agent的流式输出一个字一个字到前端
                async for chunk in self.after_sales_agent.stream_handle_after_sales(user_input, order_info, session_id):
                    yield chunk
                    
            elif intent == IntentType.PRESALES:
                # 直接传递product_agent的流式输出
                async for chunk in self.product_agent.stream_query_product(user_input, session_id):
                    yield chunk
                    
            elif intent == IntentType.GREETING:
                # 直接传递问候语的流式输出
                async for chunk in self._stream_handle_greeting(user_input):
                    yield chunk
                    
            elif intent == IntentType.UNKNOWN:
                # 直接传递未知意图的流式输出
                async for chunk in self._stream_handle_unknown_intent(user_input):
                    yield chunk
                    
            else:
                # 直接传递通用意图的流式输出
                async for chunk in self._stream_handle_general_intent(intent, user_input):
                    yield chunk
            
            # 记录流式响应完成
            await self.logger_tool.log_system_event(
                event_type="STREAM_RESPONSE_COMPLETE",
                message="流式响应完成",
                details={
                    "session_id": session_id,
                    "intent": intent.value if intent else "unknown"
                }
            )
            
        except Exception as e:
            logger.error(f"流式响应生成失败: {e}")
            await self.logger_tool.log_system_event(
                event_type="STREAM_RESPONSE_ERROR",
                message=f"流式响应失败: {e}",
                details={
                    "session_id": session_id,
                    "error": str(e)
                }
            )
            yield "抱歉，生成回答时出现错误。"

    async def _stream_handle_greeting(self, user_input: str) -> AsyncGenerator[str, None]:
        """流式处理问候语"""
        greetings = [
            "您好！欢迎使用我们的智能客服系统，我是AI助手，很高兴为您服务！请问有什么可以帮助您的吗？",
            "Hello！很高兴为您提供帮助。请告诉我您遇到了什么问题，我会尽力为您解决。",
            "您好！我是您的专属客服助手，请输入您的问题，我将为您提供专业服务。"
        ]
        
        content = random.choice(greetings)
        
        # 按字符流式输出
        for char in content:
            yield char
            # await asyncio.sleep(0.02)  # 控制输出速度
    
    async def _stream_handle_unknown_intent(self, user_input: str) -> AsyncGenerator[str, None]:
        """流式处理未知意图"""
        content = """抱歉，我没有完全理解您的问题。

我可以帮助您处理以下类型的问题：
• 商品咨询和推荐
• 订单查询和状态跟踪
• 售后服务和退换货
• 投诉建议和意见反馈

请重新描述您的问题，我会尽力为您提供帮助！"""
        
        # 按字符流式输出
        for char in content:
            yield char
            # await asyncio.sleep(0.02)  # 控制输出速度
    
    async def _stream_handle_general_intent(self, intent: IntentType, user_input: str) -> AsyncGenerator[str, None]:
        """流式处理通用意图"""
        if intent == IntentType.RECOMMENDATION:
            content = "我来为您推荐合适的产品。请告诉我您的具体需求，比如预算范围、使用场景、品牌偏好等，我会为您提供个性化的产品推荐。"
        elif intent == IntentType.COMPLAINT:
            content = "非常抱歉给您带来不好的体验。我会将您的问题和建议认真记录并反馈给相关部门。如果需要人工客服介入，我也可以为您转接。"
        else:
            content = "我正在学习中，请提供更多详细信息，我会尽力帮助您解决问题。"
        
        # 按字符流式输出
        for char in content:
            yield char
            # await asyncio.sleep(0.02)  # 控制输出速度
    
    async def _cache_hot_questions(self, user_input: str, response: str, intent: IntentType):
        """多Agent场景下的热门问题缓存逻辑"""
        try:
            # 扩展热门问题关键词列表（包含多Agent相关的热门问题）
            hot_keywords = [
                # 售后服务相关
                "退货", "退换货", "退款", "售后", "退换", "换货", "退货政策", "退换政策",
                "退货流程", "退换流程", "退货条件", "退换条件", "退货要求", "退换要求",
                
                # 订单相关
                "订单", "订单查询", "订单状态", "订单详情", "订单号", "查看订单",
                "订单进度", "发货", "配送", "快递", "物流", "收货", "签收",
                
                # 商品相关
                "商品", "产品", "库存", "价格", "规格", "尺寸", "颜色", "材质",
                "商品介绍", "产品详情", "规格参数", "使用方法", "注意事项",
                
                # 支付相关
                "支付", "付款", "支付方式", "信用卡", "支付宝", "微信支付", "银联",
                "分期付款", "花呗", "京东白条", "支付失败", "支付问题",
                
                # 会员服务相关
                "会员", "积分", "优惠券", "折扣", "活动", "促销", "满减", "包邮",
                "会员权益", "等级", "特权", "生日", "节日",
                
                # 客服相关
                "客服", "联系", "电话", "地址", "营业时间", "投诉", "建议", "反馈",
                "人工客服", "在线客服", "服务时间", "投诉处理",
                
                # 保修相关
                "保修", "维修", "更换", "质保", "保证", "质量", "问题", "故障",
                "售后服务", "技术支持", "维修网点", "维修费用",
                
                # 通用热门词汇
                "政策", "流程", "条件", "要求", "规则", "条款", "说明", "介绍",
                "帮助", "指南", "教程", "常见问题", "FAQ", "问题", "怎么办",
                "如何", "怎么", "怎样", "为什么", "什么", "哪里", "谁"
            ]
            
            # 检查是否包含热门关键词
            matched_keywords = [kw for kw in hot_keywords if kw in user_input]
            
            # 缓存条件判断（更宽松的策略）
            should_cache = False
            cache_reason = ""
            
            # 条件1：包含热门关键词且回复内容合理
            if matched_keywords and len(response) > 10:
                should_cache = True
                cache_reason = f"热门关键词匹配: {matched_keywords}，回复内容合理({len(response)}字符)"
            
            # 条件2：意图类型为热门类型且回复内容较长
            elif intent in [IntentType.AFTER_SALES, IntentType.PRESALES, IntentType.ORDER] and len(response) > 20:
                should_cache = True
                cache_reason = f"热门意图类型: {intent.value}，回复内容较长({len(response)}字符)"
            
            # 条件3：回复内容很长（高质量通用标准）
            elif len(response) > 80:
                should_cache = True
                cache_reason = f"回复内容很长，质量较高({len(response)}字符)"
            
            if should_cache:
                if redis_manager:
                    cache_success = await redis_manager.cache_response(user_input, response, ttl=300)
                    if cache_success:
                        logger.info(f"多Agent缓存问答成功: {user_input[:30]}... (原因: {cache_reason})")
                    else:
                        logger.error(f"多Agent缓存问答失败: {user_input[:30]}...")
                else:
                    logger.warning("Redis管理器未初始化，无法缓存多Agent问答")
            else:
                logger.debug(f"不缓存此多Agent回复: {user_input[:30]}... (原因: {cache_reason or '不满足缓存条件'})")
                
        except Exception as e:
            logger.error(f"缓存热门问题失败: {e}")

# 全局实例
agent_coordinator = None

def get_agent_coordinator(rag_pipeline=None) -> AgentCoordinator:
    """获取全局Agent协调器实例"""
    global agent_coordinator
    if agent_coordinator is None:
        agent_coordinator = AgentCoordinator(rag_pipeline)
    return agent_coordinator
