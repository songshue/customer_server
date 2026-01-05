"""
Redis连接管理器
处理Redis连接、断开重连、会话管理等功能
"""
import redis
import redis.asyncio as aioredis
import os
import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import uuid

logger = logging.getLogger(__name__)

class RedisManager:
    def __init__(self):
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        self.redis: Optional[aioredis.Redis] = None
        self.redis_sync: Optional[redis.Redis] = None  # 同步Redis连接
        self.session_prefix = "session:"
        self.cache_prefix = "cache:"
        self.conversation_limit = 3  # 保留最近3条消息
        
    async def connect(self):
        """连接Redis"""
        try:
            self.redis = aioredis.from_url(
                self.redis_url,
                decode_responses=True,
                retry_on_timeout=True
            )
            # 测试连接
            await self.redis.ping()
            
            # 初始化同步连接
            self.redis_sync = redis.from_url(
                self.redis_url,
                decode_responses=True
            )
            # 测试同步连接
            self.redis_sync.ping()
            
            logger.info("Redis连接成功")
            return True
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            return False
    
    async def disconnect(self):
        """断开Redis连接"""
        if self.redis:
            await self.redis.close()
            self.redis = None
        if self.redis_sync:
            self.redis_sync.close()
            self.redis_sync = None
        logger.info("Redis连接已断开")
    
    async def _ensure_connection(self):
        """确保Redis连接"""
        if not self.redis:
            await self.connect()
        return self.redis is not None
    
    async def add_message_to_session(self, session_id: str, role: str, content: str, user_id: str = None):
        """添加消息到会话历史"""
        if not await self._ensure_connection():
            return False
        
        try:
            # 生成会话键
            session_key = f"{self.session_prefix}{session_id}"
            
            # 获取现有对话历史
            existing_messages = await self.redis.get(session_key)
            if existing_messages:
                messages = json.loads(existing_messages)
            else:
                messages = []
            
            # 添加新消息
            new_message = {
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id or "unknown"
            }
            messages.append(new_message)
            
            # 保留最近3轮对话（6条消息）
            if len(messages) > self.conversation_limit * 2:
                messages = messages[-self.conversation_limit * 2:]
            
            # 存储会话历史
            await self.redis.setex(
                session_key,
                timedelta(hours=24),  # 24小时后过期
                json.dumps(messages, ensure_ascii=False)
            )
            
            logger.info(f"已添加消息到会话 {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"添加消息到会话失败: {e}")
            return False
    
    async def get_session_messages(self, session_id: str) -> List[Dict]:
        """获取会话历史消息"""
        if not await self._ensure_connection():
            return []
        
        try:
            session_key = f"{self.session_prefix}{session_id}"
            existing_messages = await self.redis.get(session_key)
            
            if existing_messages:
                messages = json.loads(existing_messages)
                return messages
            else:
                return []
                
        except Exception as e:
            logger.error(f"获取会话历史失败: {e}")
            return []
    
    async def clear_session(self, session_id: str):
        """清除会话历史"""
        if not await self._ensure_connection():
            return False
        
        try:
            session_key = f"{self.session_prefix}{session_id}"
            await self.redis.delete(session_key)
            logger.info(f"已清除会话 {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"清除会话失败: {e}")
            return False
    
    async def cache_response(self, question: str, response: str, ttl: int = 300):
        """缓存回复（默认5分钟）"""
        if not await self._ensure_connection():
            return False
        
        try:
            # 生成缓存键（将问题标准化）
            cache_key = f"{self.cache_prefix}{question.lower().strip()}"
            
            cache_data = {
                "response": response,
                "timestamp": datetime.now().isoformat(),
                "question": question
            }
            
            await self.redis.setex(
                cache_key,
                timedelta(seconds=ttl),
                json.dumps(cache_data, ensure_ascii=False)
            )
            
            logger.info(f"已缓存回复: {question[:30]}...")
            return True
            
        except Exception as e:
            logger.error(f"缓存回复失败: {e}")
            return False
    
    async def get_cached_response(self, question: str) -> Optional[Dict]:
        """获取缓存的回复"""
        if not await self._ensure_connection():
            return None
        
        try:
            cache_key = f"{self.cache_prefix}{question.lower().strip()}"
            cached_data = await self.redis.get(cache_key)
            
            if cached_data:
                try:
                    cache_info = json.loads(cached_data)
                    # 验证缓存数据的完整性
                    if isinstance(cache_info, dict) and "response" in cache_info:
                        logger.info(f"命中缓存: {question[:30]}...")
                        return cache_info
                    else:
                        logger.warning(f"缓存数据格式错误: {question[:30]}...")
                        return None
                except json.JSONDecodeError as json_error:
                    logger.error(f"JSON解析失败: {question[:30]}..., 错误: {json_error}")
                    # 删除损坏的缓存数据
                    await self.redis.delete(cache_key)
                    return None
                except Exception as data_error:
                    logger.error(f"处理缓存数据失败: {question[:30]}..., 错误: {data_error}")
                    return None
            else:
                print(f"缓存未命中: {question[:30]}...")
                return None
                
        except Exception as e:
            logger.error(f"获取缓存回复失败: {question[:30]}..., 错误: {e}")
            return None
    
    async def is_hot_question(self, question: str) -> bool:
        """判断是否为热门问题"""
        # 检查缓存中是否有该问题的回复
        cached = await self.get_cached_response(question)
        return cached is not None
    
    async def get_session_count(self) -> int:
        """获取活跃会话数量"""
        if not await self._ensure_connection():
            return 0
        
        try:
            # 获取所有session键
            pattern = f"{self.session_prefix}*"
            keys = await self.redis.keys(pattern)
            return len(keys)
            
        except Exception as e:
            logger.error(f"获取会话数量失败: {e}")
            return 0
    
    async def cleanup_expired_sessions(self):
        """清理过期的会话"""
        if not await self._ensure_connection():
            return
        
        try:
            # Redis会自动清理过期的键，这里可以添加额外的清理逻辑
            logger.info("会话清理完成")
            
        except Exception as e:
            logger.error(f"清理会话失败: {e}")

    # JWT黑名单支持方法（异步版本）
    async def setex_async(self, key: str, seconds: int, value: str) -> bool:
        """设置键值对并设置过期时间（异步方法）"""
        if not await self._ensure_connection():
            return False
        
        try:
            result = await self.redis.setex(key, seconds, value)
            # Redis的setex返回OK或None，需要转换为bool
            return result is not None
        except Exception as e:
            logger.error(f"设置键值对失败: {e}")
            return False

    async def get_async(self, key: str) -> Optional[str]:
        """获取键值（异步方法）"""
        if not await self._ensure_connection():
            return None
        
        try:
            result = await self.redis.get(key)
            return result
        except Exception as e:
            logger.error(f"获取键值失败: {e}")
            return None

    # 同步接口供security.py使用
    def setex(self, key: str, seconds: int, value: str) -> bool:
        """设置键值对并设置过期时间（同步接口）"""
        try:
            # 使用Redis的同步连接
            if hasattr(self, 'redis_sync') and self.redis_sync:
                return self.redis_sync.setex(key, seconds, value)
            else:
                # 如果没有同步Redis连接，返回False
                logger.warning("同步Redis连接不可用")
                return False
        except Exception as e:
            logger.error(f"设置键值对失败: {e}")
            return False

    async def delete_async(self, key: str) -> bool:
        """删除键值对（异步方法）"""
        if not await self._ensure_connection():
            return False
        
        try:
            result = await self.redis.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"删除键值失败: {e}")
            return False

    def get(self, key: str) -> Optional[str]:
        """获取键值（同步接口）"""
        try:
            # 使用Redis的同步连接
            if hasattr(self, 'redis_sync') and self.redis_sync:
                return self.redis_sync.get(key)
            else:
                # 如果没有同步Redis连接，返回None
                logger.warning("同步Redis连接不可用")
                return None
        except Exception as e:
            logger.error(f"获取键值失败: {e}")
            return None

# 全局Redis管理器实例
redis_manager = RedisManager()