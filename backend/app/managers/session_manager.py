"""
会话上下文管理器
管理对话历史，为Agent提供上下文信息
"""
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import uuid

from .redis_manager import redis_manager

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self):
        self.redis_manager = redis_manager
        
    async def get_conversation_context(self, session_id: str, new_message: str) -> Tuple[List[Dict], Dict]:
        """
        获取对话上下文
        
        Args:
            session_id: 会话ID
            new_message: 新消息内容
            
        Returns:
            tuple: (对话历史列表, 当前消息信息)
        """
        try:
            # 获取历史消息
            history_messages = await self.redis_manager.get_session_messages(session_id)
            
            # 构建对话上下文
            conversation_context = []
            current_message_info = {
                "content": new_message,
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id
            }
            
            # 添加历史消息到上下文
            for msg in history_messages:
                conversation_context.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # 添加当前消息
            conversation_context.append({
                "role": "user",
                "content": new_message
            })
            
            logger.info(f"会话 {session_id} 上下文构建完成，历史消息数: {len(history_messages)}")
            return conversation_context, current_message_info
            
        except Exception as e:
            logger.error(f"构建对话上下文失败: {e}")
            # 如果获取失败，返回仅有当前消息的上下文
            conversation_context = [{"role": "user", "content": new_message}]
            current_message_info = {
                "content": new_message,
                "timestamp": datetime.now().isoformat(),
                "session_id": session_id
            }
            return conversation_context, current_message_info
    
    async def add_message_to_context(self, session_id: str, role: str, content: str, user_id: str = None):
        """添加消息到会话上下文"""
        return await self.redis_manager.add_message_to_session(session_id, role, content, user_id)
    
    async def build_prompt_with_context(self, conversation_context: List[Dict]) -> str:
        """
        构建包含上下文的提示词
        
        Args:
            conversation_context: 对话历史列表
            
        Returns:
            包含上下文的提示词
        """
        try:
            # 构建对话历史文本
            conversation_text = ""
            for msg in conversation_context:
                if isinstance(msg, dict) and "role" in msg and "content" in msg:
                    if msg["role"] == "user":
                        conversation_text += f"用户: {msg['content']}\n"
                    elif msg["role"] == "assistant":
                        conversation_text += f"助手: {msg['content']}\n"
            
            # 构建系统提示词
            system_prompt = """你是一个专业的客服代表，请根据以下对话历史和当前问题提供准确、友好的回答。

注意事项：
1. 如果问题涉及公司政策、规章制度等，请基于知识库内容回答
2. 如果知识库中有相关文档，请引用具体的条款或段落
3. 保持专业、耐心、友善的服务态度
4. 如果无法确定答案，请明确说明并建议用户咨询人工客服

对话历史：
{conversation_history}

当前问题：{current_question}""".format(
                conversation_history=conversation_text.strip() if conversation_text else "无历史对话",
                current_question=(conversation_context[-1]["content"] if conversation_context and 
                             isinstance(conversation_context[-1], dict) and 
                             "content" in conversation_context[-1] else "")
            )
            
            return system_prompt
            
        except Exception as e:
            logger.error(f"构建提示词失败: {e}")
            # 返回默认提示词
            return """你是一个专业的客服代表。请基于知识库内容回答用户问题，并引用相关文档条款。"""
    
    async def should_use_cache(self, message: str) -> bool:
        """判断是否应该使用缓存"""
        # 检查是否为热门问题
        return await self.redis_manager.is_hot_question(message)
    
    async def get_cached_response(self, message: str) -> Optional[Dict]:
        """获取缓存的回复"""
        return await self.redis_manager.get_cached_response(message)
    
    async def cache_response(self, message: str, response: str, ttl: int = 300):
        """缓存回复"""
        return await self.redis_manager.cache_response(message, response, ttl)
    
    async def get_session_stats(self, session_id: str) -> Dict:
        """获取会话统计信息"""
        try:
            messages = await self.redis_manager.get_session_messages(session_id)
            return {
                "session_id": session_id,
                "message_count": len(messages),
                "first_message_time": messages[0]["timestamp"] if messages else None,
                "last_message_time": messages[-1]["timestamp"] if messages else None,
                "is_active": len(messages) > 0
            }
        except Exception as e:
            logger.error(f"获取会话统计失败: {e}")
            return {
                "session_id": session_id,
                "message_count": 0,
                "first_message_time": None,
                "last_message_time": None,
                "is_active": False
            }
    
    async def generate_session_id(self) -> str:
        """生成新的会话ID"""
        return str(uuid.uuid4())

# 全局会话管理器实例
session_manager = SessionManager()