#!/usr/bin/env python3
"""
售后Agent - 处理售后相关问题
功能：退货政策、质量问题、维修服务等售后问题
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
from ..tools.logger_tool import LoggerTool
from ..tools.redis_tool import RedisTool

# 导入共享类型
from app.models import IntentType, AgentResponse

# 配置日志
logger = logging.getLogger(__name__)

class AfterSalesAgent:
    """售后Agent - 处理售后相关问题"""
    
    def __init__(self, rag_pipeline=None, logger_tool: Optional[LoggerTool] = None, 
                 redis_tool: Optional[RedisTool] = None):
        """初始化售后Agent"""
        self.logger_tool = logger_tool or LoggerTool(logger)
        self.redis_tool = redis_tool or RedisTool()
        self.llm = self._init_llm()
        self.rag_pipeline = rag_pipeline
    
    def _init_llm(self):
        """初始化LLM模型"""
        try:
            # 使用统一的LLM配置
            llm = create_llm_with_custom_config(
                temperature=0.1,
                max_tokens=1000  # 售后问题可能需要详细的回答
            )
            
            if llm:
                return llm
            else:
                logger.warning("未找到API密钥或配置，使用模拟响应")
                return None
        except Exception as e:
            logger.error(f"初始化LLM失败: {e}")
            return None
    
    async def handle_after_sales(self, user_input: str, order_info: Dict[str, Any] = None, 
                                session_id: str = None) -> AgentResponse:
        """处理售后问题"""
        start_time = time.time()
        
        try:
            # 记录处理开始
            if self.logger_tool:
                await self.logger_tool.log_system_event(
                    event_type="AFTER_SALES_START",
                    message=f"开始处理售后问题: {user_input[:50]}...",
                    details={
                        "session_id": session_id,
                        "has_order_info": order_info is not None
                    }
                )
     
            
            # 获取售后政策信息
            policy_info = await self._get_after_sales_policy(user_input)
            
            # 生成回答
            response_content = await self._generate_response(user_input, order_info, policy_info)
            
            processing_time = time.time() - start_time
            
            # 记录处理结果
            if self.logger_tool:
                await self.logger_tool.log_system_event(
                    event_type="AFTER_SALES_COMPLETE",
                    message="售后问题处理完成",
                    details={
                        "processing_time": processing_time,
                        "policy_used": bool(policy_info.get("policies")),
                        "sources_count": len(policy_info.get("sources", []))
                    }
                )
            
            return AgentResponse(
                success=True,
                content=response_content,
                intent=IntentType.AFTER_SALES,
                sources=policy_info.get("sources", []),
                order_info=order_info,
                context={
                    "processing_time": processing_time,
                    "policy_used": bool(policy_info),
                    "session_id": session_id
                }
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"售后处理失败: {e}"
            logger.error(error_msg)
            
            # 记录错误
            if self.logger_tool:
                await self.logger_tool.log_system_event(
                    event_type="AFTER_SALES_ERROR",
                    message=error_msg,
                    details={
                        "error": str(e),
                        "processing_time": processing_time,
                        "session_id": session_id
                    }
                )
            
            return AgentResponse(
                success=False,
                content="抱歉，售后处理服务暂时不可用，请稍后重试或联系人工客服。",
                intent=IntentType.AFTER_SALES,
                context={
                    "error": str(e),
                    "processing_time": processing_time,
                    "session_id": session_id
                }
            )

    async def stream_handle_after_sales(self, user_input: str, order_info: Dict[str, Any] = None, 
                                      session_id: str = None) -> AsyncGenerator[str, None]:
        """流式处理售后问题 - 只返回实际回答内容，不包含准备信息"""
        start_time = time.time()
        
        try:
            # 记录处理开始
            if self.logger_tool:
                await self.logger_tool.log_system_event(
                    event_type="AFTER_SALES_STREAM_START",
                    message=f"开始流式处理售后问题: {user_input[:50]}...",
                    details={
                        "session_id": session_id,
                        "has_order_info": order_info is not None
                    }
                )
            
            # 获取售后政策信息
            policy_info = await self._get_after_sales_policy(user_input)
            print("policy_info121:", policy_info)
            
            # 流式生成回答 - 只返回实际有用的回答内容
            async for chunk in self._stream_generate_response(user_input, order_info, policy_info):
                yield chunk
            
            processing_time = time.time() - start_time
            
            # 记录处理结果
            if self.logger_tool:
                await self.logger_tool.log_system_event(
                    event_type="AFTER_SALES_STREAM_COMPLETE",
                    message="售后问题流式处理完成",
                    details={
                        "processing_time": processing_time,
                        "policy_used": bool(policy_info.get("policies")),
                        "sources_count": len(policy_info.get("sources", []))
                    }
                )
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"售后流式处理失败: {e}"
            logger.error(error_msg)
            
            # 记录错误
            if self.logger_tool:
                await self.logger_tool.log_system_event(
                    event_type="AFTER_SALES_STREAM_ERROR",
                    message=error_msg,
                    details={
                        "error": str(e),
                        "processing_time": processing_time,
                        "session_id": session_id
                    }
                )
            
            yield "抱歉，售后处理服务暂时不可用，请稍后重试或联系人工客服。"

    async def _stream_generate_response(self, user_input: str, order_info: Dict[str, Any] = None, 
                                      policy_info: Dict[str, Any] = None) -> AsyncGenerator[str, None]:
        """流式生成售后回答 - 真正的按字符流式输出"""
        try:
            if not self.llm:
                # 如果没有LLM，按字符流式输出简单回答
                simple_response = self._generate_simple_response(user_input, order_info, policy_info)
                for char in simple_response:
                    yield char
                    # await asyncio.sleep(0.02)  # 控制输出速度
                return
            print("policy_info:", policy_info)
            # 真正的模型流式生成 - 使用astream
            prompt = ChatPromptTemplate.from_template("""
            你是一个专业的售后客服代表。请根据用户的售后问题和相关订单信息、售后政策，提供专业、详细的售后解答。

            用户问题：{user_input}
            
            订单信息：{order_info}
            
            售后政策：{policy_info}

            请提供：
            1. 根据政策的解决方案
            2. 操作流程的详细说明
            3. 温馨提示和注意事项

            回答要求：
            - 语言友好、专业
            - 逻辑清晰
            - 提供具体操作指导
            - 包含相关政策条款
            - 回答内容必须严格依据售后政策：
            """)
            
            chain = prompt | self.llm
            
            # 使用真正的流式生成 - 直接yield每个chunk
            async for chunk in chain.astream({
                "user_input": user_input,
                "order_info": json.dumps(order_info or {}, ensure_ascii=False),
                "policy_info": json.dumps(policy_info or {}, ensure_ascii=False)
            }):
                # 直接yield模型生成的chunk内容，真正的流式输出
                chunk_content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                if chunk_content:
                    yield chunk_content
                    
        except Exception as e:
            logger.error(f"流式生成售后回答失败: {e}")
            # 降级到简单回答
            simple_response = self._generate_simple_response(user_input, order_info, policy_info)
            for char in simple_response:
                yield char
                # await asyncio.sleep(0.02)

    def _generate_simple_response(self, user_input: str, order_info: Dict[str, Any] = None, 
                                policy_info: Dict[str, Any] = None) -> str:
        """生成简单售后回答"""
        response_parts = []
        
        response_parts.append("您好！关于您的售后问题，我为您整理了相关解决方案：")
        
        if policy_info and policy_info.get("policies"):
            response_parts.append("\n📋 相关售后政策：")
            for i, policy in enumerate(policy_info["policies"][:3], 1):  # 只显示前3项
                response_parts.append(f"{i}. {policy}")
        
        if order_info:
            response_parts.append(f"\n📦 您的订单信息：")
            response_parts.append(f"• 订单号：{order_info.get('order_id', 'N/A')}")
            response_parts.append(f"• 商品名称：{order_info.get('product_name', 'N/A')}")
            response_parts.append(f"• 订单状态：{order_info.get('status', 'N/A')}")
        
        response_parts.append("\n💡 建议操作：")
        response_parts.append("• 如需退换货，请提供订单号和具体问题描述")
        response_parts.append("• 如需维修服务，请详细描述故障情况")
        response_parts.append("• 如有其他疑问，请联系人工客服")
        
        return '\n'.join(response_parts)
    
    async def _get_after_sales_policy(self, user_input: str) -> Dict[str, Any]:
        """获取售后政策信息"""
        try:
            # 首先检查Redis缓存
            cache_key = f"policy:{user_input}"
            cached_policy = await self.redis_tool.get_cached_data(cache_key)
            if cached_policy:
                logger.info(f"从缓存获取售后政策: {cache_key}")
                return cached_policy
            
            # 如果没有RAG管道，返回默认政策
            if not self.rag_pipeline:
                default_policy = {
                    "policies": [
                        "7天无理由退货",
                        "15天质量问题换货",
                        "1年免费保修",
                        "终身技术支持"
                    ],
                    "sources": []
                }
                
                # 缓存政策信息
                await self.redis_tool.cache_data(cache_key, default_policy, expire_seconds=3600)
                return default_policy
            
            # 使用RAG查询相关政策
            rag_result = await self.rag_pipeline.process_message(user_input)
            print("rag_result:", rag_result)
            # 从RAG结果中提取政策信息
            policies = []
            documents = rag_result.get("documents", [])
            
            # 从检索到的文档内容中提取政策信息
            for doc in documents:
                content = doc.get("content", "")
                if content:
                    policies.append(content)
            
            # 如果没有提取到政策，使用默认政策
            if not policies:
                policies = [
                    "7天无理由退货",
                    "15天质量问题换货",
                    "1年免费保修",
                    "终身技术支持"
                ]
            
            policy_info = {
                "policies": policies,  # 从RAG的documents中获取政策
                "sources": rag_result.get("references", [])  # 使用RAG已经处理好的references
            }
            
            # 缓存政策信息
            await self.redis_tool.cache_data(cache_key, policy_info, expire_seconds=3600)
            
            return policy_info
            
        except Exception as e:
            logger.error(f"获取售后政策失败: {e}")
            return {"policies": [], "sources": []}
    
    async def _generate_response(self, user_input: str, order_info: Dict[str, Any], policy_info: Dict[str, Any]) -> str:
        """生成售后回答"""
        try:
            if not self.llm:
                return self._generate_simple_response(user_input, order_info, policy_info)
            
            has_policies = policy_info.get("policies") and len(policy_info["policies"]) > 0
            
            if has_policies:
                policy_context = json.dumps(policy_info, ensure_ascii=False)
            else:
                policy_context = "未在知识库中找到与您问题相关的售后政策信息。请明确告知用户这一点，不要编造任何政策信息。"
            
            prompt = ChatPromptTemplate.from_template("""
你是一个专业的售后客服代表。请根据用户的问题和相关信息，提供专业、耐心的售后解答。

用户问题：{user_input}

订单信息：{order_info}

相关政策：{policy_info}

请严格遵循以下要求：
1. 如果政策信息为"未在知识库中找到相关内容"，必须明确告知用户
2. 严格禁止编造、推测或虚构任何不在文档中的政策信息
3. 如果有相关政策，引用具体的政策条款
4. 提供具体的解决方案和后续操作建议

回答要求：
- 语言友好、专业
- 逻辑清晰
- 包含具体操作步骤（基于政策内容）
- 如无政策信息，诚实告知用户并建议联系人工客服
""")
            
            chain = prompt | self.llm
            result = await chain.ainvoke({
                "user_input": user_input,
                "order_info": json.dumps(order_info, ensure_ascii=False) if order_info else "无订单信息",
                "policy_info": policy_context
            })
            
            return result.content
            
        except Exception as e:
            logger.error(f"生成售后回答失败: {e}")
            return self._generate_simple_response(user_input, order_info, policy_info)
    
    def _generate_simple_response(self, user_input: str, order_info: Dict[str, Any], policy_info: Dict[str, Any]) -> str:
        """生成简单回答"""
        response_parts = []
        
        has_policies = policy_info.get("policies") and len(policy_info["policies"]) > 0
        
        if has_policies:
            response_parts.append("您好！关于您的问题，我为您查询了相关的售后政策：")
            response_parts.append("\n我们的售后政策包括：")
            for policy in policy_info["policies"][:3]:
                response_parts.append(f"• {policy}")
        else:
            response_parts.append("您好！感谢您的咨询。")
            response_parts.append("\n未在知识库中找到与您问题相关的售后政策信息。")
        
        if order_info:
            response_parts.append(f"\n关于订单 {order_info.get('order_id', '')}：")
            response_parts.append(f"订单状态：{order_info.get('status', '未知')}")
            response_parts.append(f"商品名称：{order_info.get('product_name', '未知')}")
        
        if has_policies:
            response_parts.append("\n如果您需要进一步帮助，请联系我们的客服热线：400-123-4567")
        else:
            response_parts.append("\n为了更好地解答您的问题，建议您联系我们的客服热线：400-123-4567")
        
        return "\n".join(response_parts)
