#!/usr/bin/env python3
"""
商品Agent - 查询商品信息
功能：产品介绍、价格咨询、规格对比等售前咨询
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

class ProductAgent:
    """商品Agent - 查询商品信息"""
    
    def __init__(self, rag_pipeline=None, logger_tool: Optional[LoggerTool] = None, 
                 redis_tool: Optional[RedisTool] = None):
        """初始化商品Agent"""
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
                max_tokens=1000  # 商品查询可能需要详细介绍
            )
            
            if llm:
                return llm
            else:
                logger.warning("未找到API密钥或配置，使用模拟响应")
                return None
        except Exception as e:
            logger.error(f"初始化LLM失败: {e}")
            return None
    
    async def query_product(self, user_input: str, session_id: str = None) -> AgentResponse:
        """查询商品信息"""
        start_time = time.time()
        
        try:
            # 记录查询开始
            if self.logger_tool:
                await self.logger_tool.log_system_event(
                    event_type="PRODUCT_QUERY_START",
                    message=f"开始查询商品信息: {user_input[:50]}...",
                    details={
                        "session_id": session_id,
                        "user_input": user_input
                    }
                )
            
            # 获取商品信息
            product_info = await self._get_product_info(user_input)
            
            # 生成回答内容
            response_content = await self._generate_response(user_input, product_info)
            
            processing_time = time.time() - start_time
            
            # 记录查询结果
            if self.logger_tool:
                await self.logger_tool.log_system_event(
                    event_type="PRODUCT_QUERY_COMPLETE",
                    message="商品信息查询完成",
                    details={
                        "processing_time": processing_time,
                        "has_sources": bool(product_info.get("sources"))
                    }
                )
            
            return AgentResponse(
                success=True,
                content=response_content,
                intent=IntentType.PRESALES,
                product_info=product_info,
                sources=product_info.get("sources", []),
                context={
                    "processing_time": processing_time,
                    "session_id": session_id
                }
            )

        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"商品查询失败: {e}"
            
            # 记录查询失败
            if self.logger_tool:
                await self.logger_tool.log_system_event(
                    event_type="PRODUCT_QUERY_ERROR",
                    message=error_msg,
                    details={
                        "processing_time": processing_time,
                        "session_id": session_id,
                        "user_input": user_input
                    }
                )
            
            return AgentResponse(
                success=False,
                content=error_msg,
                intent=IntentType.PRESALES,
                context={
                    "processing_time": processing_time,
                    "session_id": session_id
                }
            )
    async def stream_query_product(self, user_input: str, session_id: str = None) -> AsyncGenerator[str, None]:
        """流式查询商品信息"""
        start_time = time.time()
        
        try:
            # 记录查询开始
            if self.logger_tool:
                await self.logger_tool.log_system_event(
                    event_type="PRODUCT_STREAM_START",
                    message=f"开始流式查询商品信息: {user_input[:50]}...",
                    details={
                        "session_id": session_id,
                        "user_input": user_input
                    }
                )
            
            # 首先发送准备信息
            yield "我正在为您查询相关商品信息..."
            
            # 获取商品信息
            product_info = await self._get_product_info(user_input)
            
            # 发送获取到的信息摘要
            if product_info:
                yield f"已找到相关商品信息，开始为您详细解答..."
            else:
                yield "抱歉，没有找到相关的商品信息，让我为您推荐其他商品..."
            
            # 流式生成回答
            async for chunk in self._stream_generate_response(user_input, product_info):
                yield chunk
            
            processing_time = time.time() - start_time
            
            # 记录查询结果
            if self.logger_tool:
                await self.logger_tool.log_system_event(
                    event_type="PRODUCT_STREAM_COMPLETE",
                    message="商品信息流式查询完成",
                    details={
                        "processing_time": processing_time,
                        "has_sources": bool(product_info.get("sources"))
                    }
                )
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"商品流式查询失败: {e}"
            logger.error(error_msg)
            
            # 记录错误
            if self.logger_tool:
                await self.logger_tool.log_system_event(
                    event_type="PRODUCT_STREAM_ERROR",
                    message=error_msg,
                    details={
                        "error": str(e),
                        "processing_time": processing_time,
                        "session_id": session_id
                    }
                )
            
            yield "抱歉，商品查询服务暂时不可用，请稍后重试。"
            
    
            
    
    async def _get_product_info(self, user_input: str) -> Dict[str, Any]:
        """获取商品信息"""
        try:
            # 首先检查Redis缓存
            cache_key = f"product:{user_input}"
            cached_product = await self.redis_tool.get_cached_data(cache_key)
            if cached_product:
                logger.info(f"从缓存获取商品信息: {cache_key}")
                return cached_product
            
            # 如果有RAG管道，使用它查询商品信息
            if self.rag_pipeline:
                relevant_docs = await self.rag_pipeline.aget_relevant_documents(user_input)
                
                if relevant_docs:
                    product_info = {
                        "description": relevant_docs[0].page_content,
                        "sources": [
                            {
                                "source": doc.metadata.get("source", "未知"),
                                "content_preview": doc.page_content[:100] + "..."
                            }
                            for doc in relevant_docs
                        ]
                    }
                    
                    # 缓存商品信息
                    await self.redis_tool.cache_data(cache_key, product_info, expire_seconds=1800)  # 30分钟缓存
                    return product_info
            
            # 模拟商品数据
            product_info = {
                "description": "我们提供多种优质的电子产品，包括智能手机、笔记本电脑、平板电脑等。所有商品均为正品行货，支持全国联保。如需了解具体产品信息，请提供更详细的需求。",
                "sources": []
            }
            
            # 缓存默认商品信息
            await self.redis_tool.cache_data(cache_key, product_info, expire_seconds=1800)
            
            return product_info
            
        except Exception as e:
            logger.error(f"获取商品信息失败: {e}")
            return {"description": "商品信息获取失败", "sources": []}
    
    async def _generate_response(self, user_input: str, product_info: Dict[str, Any]) -> str:
        """生成商品咨询回答"""
        try:
            if not self.llm:
                return self._generate_simple_response(user_input, product_info)
            
            has_product_info = product_info.get("description") or product_info.get("products")
            
            if has_product_info:
                product_context = json.dumps(product_info, ensure_ascii=False)
            else:
                product_context = "未在商品库中找到与您咨询相关的产品信息。请明确告知用户这一点，不要编造任何产品信息。"
            
            prompt = ChatPromptTemplate.from_template("""
你是一个专业的售前客服代表。请根据用户的咨询问题和相关商品信息，提供专业、详细的售前解答。

用户咨询：{user_input}

商品信息：{product_info}

请严格遵循以下要求：
1. 如果商品信息为"未在商品库中找到相关内容"，必须明确告知用户
2. 严格禁止编造、推测或虚构任何不在文档中的产品信息
3. 如果有相关商品，详细介绍产品特点、参数和购买建议
4. 回答用户的具体问题

回答要求：
- 语言友好、专业
- 逻辑清晰
- 包含具体产品参数（基于商品信息）
- 如无商品信息，诚实告知用户并建议提供更多需求信息
""")
            
            chain = prompt | self.llm
            result = await chain.ainvoke({
                "user_input": user_input,
                "product_info": product_context
            })
            
            return result.content
            
        except Exception as e:
            logger.error(f"生成商品回答失败: {e}")
            return self._generate_simple_response(user_input, product_info)
    
    async def _stream_generate_response(self, user_input: str, product_info: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """流式生成商品咨询回答"""
        try:
            if not self.llm:
                simple_response = self._generate_simple_response(user_input, product_info)
                for char in simple_response:
                    yield char
                return
            
            has_product_info = product_info.get("description") or product_info.get("products")
            
            if has_product_info:
                product_context = json.dumps(product_info, ensure_ascii=False)
            else:
                product_context = "未在商品库中找到与您咨询相关的产品信息。请明确告知用户这一点，不要编造任何产品信息。"
            
            prompt = ChatPromptTemplate.from_template("""
你是一个专业的售前客服代表。请根据用户的咨询问题和相关商品信息，提供专业、详细的售前解答。

用户咨询：{user_input}

商品信息：{product_info}

请严格遵循以下要求：
1. 如果商品信息为"未在商品库中找到相关内容"，必须明确告知用户
2. 严格禁止编造、推测或虚构任何不在文档中的产品信息
3. 如果有相关商品，详细介绍产品特点、参数和购买建议
4. 回答用户的具体问题

回答要求：
- 语言友好、专业
- 逻辑清晰
- 包含具体产品参数（基于商品信息）
- 如无商品信息，诚实告知用户并建议提供更多需求信息
""")
            
            chain = prompt | self.llm
            
            async for chunk in chain.astream({
                "user_input": user_input,
                "product_info": product_context
            }):
                if chunk.content:
                    yield chunk.content
                    
        except Exception as e:
            logger.error(f"流式生成商品回答失败: {e}")
            simple_response = self._generate_simple_response(user_input, product_info)
            for char in simple_response:
                yield char

    def _generate_simple_response(self, user_input: str, product_info: Dict[str, Any]) -> str:
        """生成简单回答"""
        response_parts = []
        
        has_product_info = product_info.get("description") or product_info.get("products")
        
        if has_product_info:
            response_parts.append("您好！关于您的咨询，我为您整理了相关商品信息：")
            
            if product_info.get("description"):
                response_parts.append(f"\n{product_info['description']}")
            
            response_parts.append("\n如需了解更多具体产品信息，请提供以下信息：")
            response_parts.append("• 具体产品类别（如手机、电脑等）")
            response_parts.append("• 价格预算范围")
            response_parts.append("• 使用需求（如办公、游戏、摄影等）")
            response_parts.append("• 品牌偏好")
            
            response_parts.append("\n我们的专业顾问将为您提供个性化的产品推荐！")
        else:
            response_parts.append("您好！感谢您的咨询。")
            response_parts.append("\n未在商品库中找到与您咨询相关的产品信息。")
            response_parts.append("\n为了更好地为您提供产品推荐，请提供以下信息：")
            response_parts.append("• 具体产品类别（如手机、电脑等）")
            response_parts.append("• 价格预算范围")
            response_parts.append("• 使用需求（如办公、游戏、摄影等）")
            response_parts.append("• 品牌偏好")
            response_parts.append("\n您也可以联系我们的客服热线：400-123-4567 获取专业推荐！")
        
        return "\n".join(response_parts)
