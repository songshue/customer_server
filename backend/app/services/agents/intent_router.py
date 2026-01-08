#!/usr/bin/env python3
"""
意图路由Agent - 智能客服主路由系统
功能：分析用户输入，判断用户真实意图
"""
import os
import sys
import json
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import re
from enum import Enum
from pydantic import BaseModel

# 导入LLM配置
from ..llm_config import create_llm_with_custom_config
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

# 确保当前目录在Python路径中
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 导入工具
try:
    from ..tools.logger_tool import LoggerTool
except ImportError as e:
    logging.warning(f"导入LoggerTool失败: {e}")
    LoggerTool = None

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入共享类型
from app.models import IntentType, AgentResponse

class IntentRouterAgent:
    """主路由Agent - 判断用户意图"""
    
    def __init__(self, logger_tool: Optional[LoggerTool] = None):
        """初始化主路由Agent"""
        self.logger_tool = logger_tool
        self.llm = self._init_llm()
        self.intent_prompt = ChatPromptTemplate.from_template("""
                你是一个智能客服主路由系统。请分析用户输入，判断用户的真实意图。

        任务：根据用户消息判断意图类型
        输出格式：JSON格式

        意图类型定义：
        - presales: 售前咨询（未下单前的产品介绍、价格、规格、库存、优惠等问题）
        - order: 订单相关（查询、修改、取消尚未发货的订单；涉及订单号但未提及收货后问题）
        - logistics: 物流配送（询问发货时间、快递单号、配送延迟、未收到货等运输中问题）
        - after_sales: 售后问题（用户已收到商品或确认交易完成，提出以下任一需求：退货、换货、维修、补发、部分退款、质量问题反馈、商品破损/缺失/发错/与描述不符、功能异常、申请售后凭证等。即使语气不满，只要核心诉求是解决商品问题，即归为此类）
        - recommendation: 商品推荐（明确要求“推荐”“有没有适合...的”等）
        - complaint: 投诉建议（无具体售后商品处理诉求，仅表达对服务、态度、平台规则的不满，或要求赔偿、曝光、找领导等）
        - greeting: 问候语（如你好、再见、感谢等）
        - unknown: 无法确定意图（与电商无关、语义模糊、测试语句等）

        判断优先级：after_sales > complaint（当同时涉及商品问题和情绪时，优先 after_sales）

        上下文信息：
        {context}

        用户输入：{user_input}

        请严格按照以下JSON格式返回，不要包含其他内容：
        {{
            "intent": "意图类型",
            "confidence": 0.95,
            "extracted_info": {{
                "order_id": "订单号（如果包含）",
                "product_type": "产品类型（如果提及）",
                "keywords": ["关键词列表"]
            }},
            "reasoning": "判断理由"
        }}
        """)
        
        self.output_parser = JsonOutputParser()
    
    def _init_llm(self):
        """初始化LLM模型"""
        try:
            # 使用统一的LLM配置
            llm = create_llm_with_custom_config(
                temperature=0.1,
                max_tokens=500  # 意图识别不需要太长的输出
            )
            
            if llm:
                return llm
            else:
                logger.warning("未找到API密钥或配置，使用模拟响应")
                return None
        except Exception as e:
            logger.error(f"初始化LLM失败: {e}")
            return None
    
    async def route(self, user_input: str, context: Dict[str, Any] = None) -> AgentResponse:
        """路由用户输入"""
        start_time = time.time()
        
        try:
            if context is None:
                context = {}
            
            # 如果没有LLM，使用规则匹配
            if not self.llm:
                return await self._rule_based_routing(user_input)
            
            # 使用LLM进行意图识别
            chain = self.intent_prompt | self.llm | self.output_parser
            result = await chain.ainvoke({
                "user_input": user_input,
                "context": json.dumps(context, ensure_ascii=False)
            })
            
            intent = IntentType(result.get("intent", "unknown"))
            confidence = result.get("confidence", 0.0)
            extracted_info = result.get("extracted_info", {})
            reasoning = result.get("reasoning", "")
            
            processing_time = time.time() - start_time
            
            # 记录路由结果
            if self.logger_tool:
                await self.logger_tool.log_system_event(
                    event_type="INTENT_ROUTED",
                    message=f"意图路由完成: {intent.value}",
                    details={
                        "user_input": user_input,
                        "intent": intent.value,
                        "confidence": confidence,
                        "extracted_info": extracted_info,
                        "reasoning": reasoning,
                        "processing_time": processing_time
                    }
                )
            
            return AgentResponse(
                success=True,
                content=f"已识别用户意图：{intent.value}",
                intent=intent,
                context={
                    "confidence": confidence,
                    "extracted_info": extracted_info,
                    "reasoning": reasoning,
                    "processing_time": processing_time
                }
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"意图路由失败: {e}")
            
            if self.logger_tool:
                await self.logger_tool.log_error('intent_routing_error', str(e), {
                    'user_input': user_input,
                    'context': context,
                    'processing_time': processing_time
                })
            
            return AgentResponse(
                success=False,
                content="抱歉，无法识别您的意图，请重新描述您的问题。",
                intent=IntentType.UNKNOWN
            )
    
    async def _rule_based_routing(self, user_input: str) -> AgentResponse:
        """基于规则的意图识别"""
        user_input_lower = user_input.lower()
        
        # 订单相关关键词（仅操作类）
        order_keywords = ["订单", "购买", "下单", "付款", "取消订单", "修改订单"]
        if any(keyword in user_input_lower for keyword in order_keywords):
            return AgentResponse(
                success=True,
                content="检测到订单相关咨询",
                intent=IntentType.ORDER,
                context={"routing_method": "rule_based"}
            )
        
        # 物流相关关键词 - 只有包含具体单号才使用物流查询
        # 如果只是问一般性问题（如"多久能发货"），会路由到售后Agent查询知识库
        logistics_with_number = [
            r"快递单号[：:\s]*[A-Za-z0-9]+",
            r"单号[：:\s]*[A-Za-z0-9]+",
            r"运单号[：:\s]*[A-Za-z0-9]+",
            r"[A-Za-z0-9]{8,}",  # 假设快递单号至少8位
            r"订单号[：:\s]*[A-Za-z0-9]+",
        ]
        has_tracking_number = any(re.search(pattern, user_input) for pattern in logistics_with_number)
        
        if has_tracking_number:
            # 提取订单号/快递单号
            extracted_info = {}
            for pattern in logistics_with_number:
                match = re.search(pattern, user_input)
                if match:
                    if "单号" in pattern or "订单号" in pattern:
                        extracted_info["tracking_number"] = match.group().split("号")[-1].strip("：: \t")
                    else:
                        extracted_info["tracking_number"] = match.group()
                    break
            
            return AgentResponse(
                success=True,
                content="检测到物流查询（包含单号）",
                intent=IntentType.LOGISTICS,
                context={
                    "routing_method": "rule_based",
                    "extracted_info": extracted_info
                }
            )
        
        # 物流相关关键词 - 没有单号则路由到售后Agent查询知识库
        logistics_keywords = ["发货", "配送", "快递", "物流", "到货", "运输", "发货时间"]
        if any(keyword in user_input_lower for keyword in logistics_keywords):
            return AgentResponse(
                success=True,
                content="检测到物流配送咨询（将查询知识库）",
                intent=IntentType.AFTER_SALES,
                context={"routing_method": "rule_based"}
            )
        
        # 售后相关关键词
        after_sales_keywords = ["退货", "退款", "换货", "质量", "问题", "维修", "投诉"]
        if any(keyword in user_input_lower for keyword in after_sales_keywords):
            return AgentResponse(
                success=True,
                content="检测到售后相关咨询",
                intent=IntentType.AFTER_SALES,
                context={"routing_method": "rule_based"}
            )
        
        # 商品相关关键词
        product_keywords = ["手机", "电脑", "平板", "产品", "价格", "配置", "参数"]
        if any(keyword in user_input_lower for keyword in product_keywords):
            return AgentResponse(
                success=True,
                content="检测到商品相关咨询",
                intent=IntentType.PRESALES,
                context={"routing_method": "rule_based"}
            )
        
        # 问候语
        greeting_keywords = ["你好", "hello", "hi", "再见", "拜拜", "谢谢", "感谢"]
        if any(keyword in user_input_lower for keyword in greeting_keywords):
            return AgentResponse(
                success=True,
                content="检测到问候语",
                intent=IntentType.GREETING,
                context={"routing_method": "rule_based"}
            )
        
        return AgentResponse(
            success=True,
            content="无法确定具体意图",
            intent=IntentType.UNKNOWN,
            context={"routing_method": "rule_based"}
        )