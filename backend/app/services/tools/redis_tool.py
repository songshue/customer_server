#!/usr/bin/env python3
"""
Redis工具 - 提供Redis操作相关的工具函数
"""
import os
import sys
import logging
from typing import Dict, Any, Optional, List
import json
import time

# 确保当前目录在Python路径中
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 导入Redis管理器
try:
    from ...managers.redis_manager import redis_manager
except ImportError as e:
    logging.warning(f"导入redis_manager失败: {e}")
    redis_manager = None

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RedisTool:
    """Redis工具类"""
    
    def __init__(self, redis_client=None):
        """初始化Redis工具"""
        self.redis_client = redis_client or redis_manager
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def get_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话数据"""
        try:
            if not self.redis_client:
                self.logger.warning("Redis客户端未初始化")
                return None
            
            key = f"session:{session_id}"
            data = await self.redis_client.get_async(key)
            
            if data:
                return json.loads(data)
            
            return None
            
        except Exception as e:
            self.logger.error(f"获取会话数据失败: {e}")
            return None
    
    async def save_session_data(self, session_id: str, data: Dict[str, Any], 
                               expire_seconds: int = 3600) -> bool:
        """保存会话数据"""
        try:
            if not self.redis_client:
                return False
            
            key = f"session:{session_id}"
            data_json = json.dumps(data, ensure_ascii=False, default=str)
            
            await self.redis_client.setex_async(key, expire_seconds, data_json)
            
            self.logger.debug(f"会话数据已保存: {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存会话数据失败: {e}")
            return False
    
    async def delete_session_data(self, session_id: str) -> bool:
        """删除会话数据"""
        try:
            if not self.redis_client:
                return False
            
            key = f"session:{session_id}"
            await self.redis_client.delete(key)
            
            self.logger.debug(f"会话数据已删除: {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"删除会话数据失败: {e}")
            return False
    
    async def get_user_context(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户上下文"""
        try:
            if not self.redis_client:
                return None
            
            key = f"user_context:{user_id}"
            data = await self.redis_client.get_async(key)
            
            if data:
                return json.loads(data)
            
            return None
            
        except Exception as e:
            self.logger.error(f"获取用户上下文失败: {e}")
            return None
    
    async def save_user_context(self, user_id: str, context: Dict[str, Any], 
                               expire_seconds: int = 7200) -> bool:
        """保存用户上下文"""
        try:
            if not self.redis_client:
                return False
            
            key = f"user_context:{user_id}"
            context_json = json.dumps(context, ensure_ascii=False, default=str)
            
            await self.redis_client.setex_async(key, expire_seconds, context_json)
            
            self.logger.debug(f"用户上下文已保存: {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存用户上下文失败: {e}")
            return False
    
    async def increment_counter(self, key: str, expire_seconds: int = None) -> int:
        """增加计数器"""
        try:
            if not self.redis_client:
                return 0
            
            # RedisManager没有提供异步的incr方法，需要使用其他方式实现
            # 这里暂时返回0，后续可以扩展RedisManager支持更多异步操作
            self.logger.warning("RedisManager未实现异步计数器功能")
            return 0
                
        except Exception as e:
            self.logger.error(f"增加计数器失败: {e}")
            return 0
    
    async def get_cached_data(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        try:
            if not self.redis_client:
                return None
            
            data = await self.redis_client.get_async(key)
            
            if data:
                return json.loads(data)
            
            return None
            
        except Exception as e:
            self.logger.error(f"获取缓存失败: {e}")
            return None
    
    async def cache_data(self, key: str, value: Any, expire_seconds: int = 300) -> bool:
        """缓存数据（与cache_data方法兼容）"""
        try:
            if not self.redis_client:
                self.logger.warning("Redis客户端未初始化")
                return False
            
            value_json = json.dumps(value, ensure_ascii=False, default=str)
            
            await self.redis_client.setex_async(key, expire_seconds, value_json)
            
            self.logger.debug(f"缓存数据已设置: {key}")
            return True
            
        except Exception as e:
            self.logger.error(f"缓存数据失败: {e}")
            return False
    
    async def set_cache(self, key: str, value: Any, expire_seconds: int = 300) -> bool:
        """设置缓存数据"""
        try:
            if not self.redis_client:
                return False
            
            value_json = json.dumps(value, ensure_ascii=False, default=str)
            
            await self.redis_client.setex_async(key, expire_seconds, value_json)
            
            self.logger.debug(f"缓存数据已设置: {key}")
            return True
            
        except Exception as e:
            self.logger.error(f"设置缓存失败: {e}")
            return False
    
    async def delete_cache(self, key: str) -> bool:
        """删除缓存数据"""
        try:
            if not self.redis_client:
                return False
            
            result = await self.redis_client.delete_async(key)
            
            if result:
                self.logger.debug(f"缓存数据已删除: {key}")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"删除缓存失败: {e}")
            return False
    
    async def add_to_list(self, key: str, *values: Any) -> int:
        """向列表添加元素"""
        try:
            if not self.redis_client:
                return 0
            
            # RedisManager没有提供异步的lpush方法，需要使用其他方式实现
            # 这里暂时返回0，后续可以扩展RedisManager支持更多异步操作
            self.logger.warning("RedisManager未实现异步列表操作功能")
            return 0
            
        except Exception as e:
            self.logger.error(f"向列表添加元素失败: {e}")
            return 0
    
    async def get_list_range(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        """获取列表范围"""
        try:
            if not self.redis_client:
                return []
            
            # RedisManager没有提供异步的lrange方法，需要使用其他方式实现
            # 这里暂时返回空列表，后续可以扩展RedisManager支持更多异步操作
            self.logger.warning("RedisManager未实现异步列表操作功能")
            return []
            
        except Exception as e:
            self.logger.error(f"获取列表范围失败: {e}")
            return []