"""
MySQL数据库管理器
负责存储完整的聊天记录到数据库
"""
import os
import asyncio
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import aiomysql
import json

logger = logging.getLogger(__name__)

class MySQLManager:
    """MySQL数据库管理器"""
    
    def __init__(self):
        self.db_url = os.getenv('DATABASE_URL')
        self.connection_pool: Optional[aiomysql.Pool] = None
        self.table_name = "chat_messages"
        
        # 解析数据库连接信息
        self._parse_db_url()
    
    def _parse_db_url(self):
        """解析数据库配置"""
        # 优先使用DATABASE_URL，否则使用分开的配置
        if not self.db_url:
            logger.warning("未找到DATABASE_URL配置，使用分开的配置")
            from app.core.config import settings
            
            self.db_config = {
                'host': settings.mysql_host,
                'port': settings.mysql_port,
                'user': settings.mysql_user,
                'password': settings.mysql_password,
                'db': settings.mysql_database,
                'charset': 'utf8mb4'
            }
            return
        
        # 解析格式：mysql://username:password@host:port/database
        try:
            if "://" in self.db_url:
                url_parts = self.db_url.split("://")[1]
                auth_host, db_name = url_parts.split("/")
                
                if "@" in auth_host:
                    auth_info, host_port = auth_host.split("@")
                    username, password = auth_info.split(":")
                    host, port = host_port.split(":")
                else:
                    username = "root"
                    password = ""
                    host, port = auth_host.split(":")
                    db_name = db_name
                
                self.db_config = {
                    "host": host,
                    "port": int(port),
                    "user": username,
                    "password": password,
                    "db": db_name,
                    "charset": "utf8mb4"
                }
                logger.info(f"解析数据库配置成功: {host}:{port}/{db_name}")
            else:
                logger.error("DATABASE_URL格式不正确")
                self.db_config = None
                
        except Exception as e:
            logger.error(f"解析DATABASE_URL失败: {e}")
            self.db_config = None
    
    async def connect(self):
        """连接MySQL数据库"""
        if not self.db_config:
            logger.warning("数据库配置无效，跳过MySQL连接")
            return False
        
        try:
            self.connection_pool = await aiomysql.create_pool(
                **self.db_config,
                minsize=2,  # 增加最小连接数
                maxsize=10,  # 增加最大连接数以支持更多并发
                connect_timeout=30,  # 连接超时时间
            )
            
            # 测试连接并创建表
            await self._create_table_if_not_exists()
            logger.info("MySQL连接成功")
            return True
            
        except Exception as e:
            logger.error(f"MySQL连接失败: {e}")
            return False
    
    async def disconnect(self):
        """断开MySQL连接"""
        if self.connection_pool:
            self.connection_pool.close()
            await self.connection_pool.wait_closed()
            self.connection_pool = None
            logger.info("MySQL连接已断开")
    
    async def cleanup_old_messages(self, days_to_keep=30) -> int:
        """
        清理指定天数之前的旧消息
        
        Args:
            days_to_keep: 保留最近多少天的消息，默认30天
            
        Returns:
            删除的消息数量
        """
        if not self.connection_pool:
            logger.warning("MySQL未连接，跳过消息清理")
            return 0
        
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # 计算保留的时间点
                    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
                    
                    # 执行删除操作
                    delete_sql = f"""
                    DELETE FROM {self.table_name}
                    WHERE created_at < %s
                    """
                    
                    await cursor.execute(delete_sql, (cutoff_date,))
                    deleted_count = cursor.rowcount
                    
                    logger.info(f"成功清理 {deleted_count} 条 {days_to_keep} 天前的旧消息")
                    return deleted_count
                    
        except Exception as e:
            logger.error(f"清理旧消息失败: {e}")
            return 0
    
    async def _create_table_if_not_exists(self):
        """创建必要的表（如果不存在）"""
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # 创建聊天消息表
                    create_messages_table_sql = f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        session_id VARCHAR(255) NOT NULL,
                        user_id VARCHAR(255) NOT NULL,
                        message_type VARCHAR(20) NOT NULL,
                        content TEXT NOT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        message_metadata JSON,
                        INDEX idx_session_id (session_id),
                        INDEX idx_message_type (message_type),
                        INDEX idx_created_at (created_at),
                        INDEX idx_user_id (user_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                    
                    await cursor.execute(create_messages_table_sql)
                    logger.info(f"创建表 {self.table_name} 成功")
                    print(f"创建表 {self.table_name} 成功")
                    
                    # 创建聊天会话表
                    create_sessions_table_sql = """
                    CREATE TABLE IF NOT EXISTS chat_sessions (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        session_id VARCHAR(255) UNIQUE NOT NULL,
                        user_id VARCHAR(255) NOT NULL,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        last_activity DATETIME NOT NULL,
                        status ENUM('active', 'archived', 'deleted') DEFAULT 'active',
                        session_metadata JSON,
                        INDEX idx_user_id (user_id),
                        INDEX idx_last_activity (last_activity),
                        INDEX idx_status (status)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                    
                    await cursor.execute(create_sessions_table_sql)
                    logger.info("创建表 chat_sessions 成功")
                    
        except Exception as e:
            logger.error(f"创建表失败: {e}")
            raise
    
    async def create_session(self, user_id: str, session_id: str, title: str = None) -> bool:
        """创建新会话"""
        if not self.connection_pool:
            return False
        
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # 检查会话是否已存在
                    check_sql = "SELECT id FROM chat_sessions WHERE session_id = %s"
                    await cursor.execute(check_sql, (session_id,))
                    
                    if await cursor.fetchone():
                        logger.warning(f"会话已存在: {session_id}")
                        return True
                    
                    # 创建新会话记录
                    insert_sql = """
                    INSERT INTO chat_sessions (session_id, user_id, created_at, updated_at, last_activity, session_metadata)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    current_time = datetime.now()
                    metadata = {"title": title or "新会话"} if title else None
                    metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None
                    
                    await cursor.execute(insert_sql, (
                        session_id, user_id, current_time, current_time, current_time, metadata_json
                    ))
                    
                    logger.info(f"创建新会话: {session_id} - {title or '新会话'}")
                    return True
                    
        except Exception as e:
            logger.error(f"创建会话失败: {e}")
            return False
    
    async def create_session_if_not_exists(self, session_id: str, user_id: str) -> bool:
        """创建会话记录（如果不存在）"""
        if not self.connection_pool:
            return False
        
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # 检查会话是否已存在
                    check_sql = "SELECT id FROM chat_sessions WHERE session_id = %s"
                    await cursor.execute(check_sql, (session_id,))
                    
                    if not await cursor.fetchone():
                        # 会话不存在，创建新记录
                        insert_sql = """
                        INSERT INTO chat_sessions (session_id, user_id, created_at, updated_at, last_activity)
                        VALUES (%s, %s, %s, %s, %s)
                        """
                        current_time = datetime.now()
                        await cursor.execute(insert_sql, (
                            session_id, user_id, current_time, current_time, current_time
                        ))
                        logger.info(f"创建新会话记录: {session_id}")
                    else:
                        # 会话已存在，更新最后活动时间
                        await self.update_session_activity(session_id)
                    
                    return True
                    
        except Exception as e:
            logger.error(f"创建会话记录失败: {e}")
            return False
    
    async def update_session_activity(self, session_id: str) -> bool:
        """更新会话的最后活动时间"""
        if not self.connection_pool:
            return False
        
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    update_sql = """
                    UPDATE chat_sessions 
                    SET last_activity = %s, updated_at = %s
                    WHERE session_id = %s
                    """
                    current_time = datetime.now()
                    await cursor.execute(update_sql, (current_time, current_time, session_id))
                    
                    if cursor.rowcount > 0:
                        logger.debug(f"更新会话活动时间: {session_id}")
                        return True
                    else:
                        logger.warning(f"未找到会话记录: {session_id}")
                        return False
                        
        except Exception as e:
            logger.error(f"更新会话活动时间失败: {e}")
            return False

    async def save_message(self, session_id: str, user_id: str, role: str, 
                          content: str, metadata: Optional[Dict] = None) -> bool:
        """保存单条消息到数据库"""
        if not self.connection_pool:
            logger.warning("MySQL未连接，跳过消息保存")
            return False
        
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    insert_sql = f"""
                    INSERT INTO {self.table_name} 
                    (session_id, user_id, message_type, content, created_at, message_metadata)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    
                    created_at = datetime.now()
                    metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None
                    
                    await cursor.execute(insert_sql, (
                        session_id, user_id, role, content, created_at, metadata_json
                    ))
                    
                    logger.info(f"保存消息成功: {session_id} - {role}")
                    return True
                    
        except Exception as e:
            logger.error(f"保存消息失败: {e}")
            return False
    
    async def save_conversation_batch(self, messages: List[Dict], session_id: str = None) -> bool:
        """批量保存对话消息"""
        if not self.connection_pool:
            logger.warning("MySQL未连接，跳过批量保存")
            return False
        
        if not messages:
            return True
        
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    insert_sql = f"""
                    INSERT INTO {self.table_name} 
                    (session_id, user_id, message_type, content, created_at, message_metadata)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    
                    # 批量插入
                    values_list = []
                    for msg in messages:
                        created_at = datetime.fromisoformat(msg.get("created_at", datetime.now().isoformat()))
                        metadata_json = json.dumps(msg.get("metadata", {}), ensure_ascii=False)
                        
                        values_list.append((
                            msg.get("session_id", session_id or "unknown"),
                            msg.get("user_id", "unknown"),
                            msg.get("message_type"),
                            msg.get("content"),
                            created_at,
                            metadata_json
                        ))
                    
                    await cursor.executemany(insert_sql, values_list)
                    logger.info(f"批量保存 {len(messages)} 条消息成功")
                    return True
                    
        except Exception as e:
            logger.error(f"批量保存消息失败: {e}")
            return False
    
    async def get_conversation_history(self, session_id: str, limit: int = 100) -> List[Dict]:
        """获取对话历史"""
        if not self.connection_pool:
            return []
        
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    select_sql = f"""
                    SELECT * FROM {self.table_name}
                    WHERE session_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """
                    
                    await cursor.execute(select_sql, (session_id, limit))
                    results = await cursor.fetchall()
                    
                    # 按时间正序返回
                    if results:
                        results = list(results)
                        results.reverse()
                    
                    logger.info(f"获取对话历史: {session_id} - {len(results)} 条消息")
                    return results
                    
        except Exception as e:
            logger.error(f"获取对话历史失败: {e}")
            return []
    
    async def get_user_conversations(self, user_id: str, limit: int = 50) -> List[Dict]:
        """获取用户的所有对话"""
        if not self.connection_pool:
            return []
        
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    select_sql = f"""
                    SELECT session_id, MIN(created_at) as start_time, MAX(created_at) as end_time,
                           COUNT(*) as message_count
                    FROM {self.table_name}
                    WHERE user_id = %s
                    GROUP BY session_id
                    ORDER BY start_time DESC
                    LIMIT %s
                    """
                    
                    await cursor.execute(select_sql, (user_id, limit))
                    results = await cursor.fetchall()
                    
                    logger.info(f"获取用户对话: {user_id} - {len(results)} 个会话")
                    return results
                    
        except Exception as e:
            logger.error(f"获取用户对话失败: {e}")
            return []
    
    async def cleanup_old_messages(self, days: int = 30):
        """清理旧消息"""
        if not self.connection_pool:
            return
        
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    delete_sql = f"""
                    DELETE FROM {self.table_name}
                    WHERE created_at < DATE_SUB(NOW(), INTERVAL %s DAY)
                    """
                    
                    await cursor.execute(delete_sql, (days,))
                    logger.info(f"清理 {days} 天前的消息完成")
                    
        except Exception as e:
            logger.error(f"清理旧消息失败: {e}")
    
    async def get_conversation_stats(self) -> Dict[str, Any]:
        """获取对话统计信息"""
        if not self.connection_pool:
            return {}
        
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    # 总消息数
                    total_sql = f"SELECT COUNT(*) as total_messages FROM {self.table_name}"
                    await cursor.execute(total_sql)
                    total_result = await cursor.fetchone()
                    
                    # 今日消息数
                    today_sql = f"""
                    SELECT COUNT(*) as today_messages FROM {self.table_name}
                    WHERE DATE(created_at) = CURDATE()
                    """
                    await cursor.execute(today_sql)
                    today_result = await cursor.fetchone()
                    
                    # 活跃会话数
                    active_sql = f"""
                    SELECT COUNT(DISTINCT session_id) as active_sessions 
                    FROM {self.table_name}
                    WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                    """
                    await cursor.execute(active_sql)
                    active_result = await cursor.fetchone()
                    
                    stats = {
                        "total_messages": total_result.get("total_messages", 0),
                        "today_messages": today_result.get("today_messages", 0),
                        "active_sessions_24h": active_result.get("active_sessions", 0)
                    }
                    
                    logger.info(f"获取对话统计: {stats}")
                    return stats
                    
        except Exception as e:
            logger.error(f"获取对话统计失败: {e}")
            return {}
    
    async def get_user_sessions(self, user_id: str) -> List[Dict]:
        """获取用户的会话列表"""
        if not self.connection_pool:
            return []
        
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    # 从chat_sessions表获取会话列表
                    select_sql = """
                    SELECT session_id, created_at, updated_at, last_activity, 
                           status, session_metadata,
                           (SELECT COUNT(*) FROM chat_messages cm WHERE cm.session_id = cs.session_id) as message_count,
                           (SELECT content FROM chat_messages cm2 WHERE cm2.session_id = cs.session_id 
                            ORDER BY cm2.created_at DESC LIMIT 1) as last_message
                    FROM chat_sessions cs
                    WHERE user_id = %s
                    ORDER BY last_activity DESC
                    """
                    
                    await cursor.execute(select_sql, (user_id,))
                    results = await cursor.fetchall()
                    
                    logger.info(f"获取用户会话列表: {user_id} - {len(results)} 个会话")
                    return results
                    
        except Exception as e:
            logger.error(f"获取用户会话列表失败: {e}")
            return []
    
    async def delete_session(self, session_id: str) -> bool:
        """删除会话及其所有消息"""
        if not self.connection_pool:
            return False
        
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # 删除会话消息
                    delete_messages_sql = "DELETE FROM chat_messages WHERE session_id = %s"
                    await cursor.execute(delete_messages_sql, (session_id,))
                    
                    # 删除会话记录
                    delete_session_sql = "DELETE FROM chat_sessions WHERE session_id = %s"
                    await cursor.execute(delete_session_sql, (session_id,))
                    
                    logger.info(f"删除会话: {session_id}")
                    return True
                    
        except Exception as e:
            logger.error(f"删除会话失败: {e}")
            return False

    async def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """
        执行查询操作
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            查询结果列表
        """
        if not self.connection_pool:
            logger.warning("MySQL未连接，跳过查询执行")
            return []
        
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    if params:
                        await cursor.execute(query, params)
                    else:
                        await cursor.execute(query)
                    
                    results = await cursor.fetchall()
                    logger.info(f"查询执行成功: {len(results)} 条记录")
                    return results
                    
        except Exception as e:
            logger.error(f"查询执行失败: {e}")
            return []
    
    async def rename_session(self, session_id: str, title: str) -> bool:
        """重命名会话"""
        if not self.connection_pool:
            return False
        
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # 更新会话元数据
                    update_sql = """
                    UPDATE chat_sessions 
                    SET session_metadata = %s, updated_at = %s
                    WHERE session_id = %s
                    """
                    current_time = datetime.now()
                    await cursor.execute(update_sql, (title, current_time, session_id))
                    
                    logger.info(f"重命名会话: {session_id} -> {title}")
                    return True
                    
        except Exception as e:
            logger.error(f"重命名会话失败: {e}")
            return False
    
    async def get_session_user_id(self, session_id: str) -> Optional[str]:
        """获取会话所属的用户ID"""
        if not self.connection_pool:
            return None
        
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    select_sql = "SELECT user_id FROM chat_sessions WHERE session_id = %s"
                    await cursor.execute(select_sql, (session_id,))
                    result = await cursor.fetchone()
                    
                    if result:
                        return result[0]  # user_id is at index 0
                    return None
                    
        except Exception as e:
            logger.error(f"获取会话用户ID失败: {e}")
            return None
    
    async def save_feedback(self, message_id: int, session_id: str, user_id: str, rating: int, comment: str = None) -> bool:
        """
        保存用户反馈
        
        Args:
            message_id: 消息ID
            session_id: 会话ID
            user_id: 用户ID
            rating: 评分 (1-5)
            comment: 评论内容
            
        Returns:
            是否保存成功
        """
        if not self.connection_pool:
            logger.warning("MySQL未连接，跳过反馈保存")
            return False
        
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # 检查用户反馈表是否存在，如果不存在则创建
                    create_feedback_table_sql = """
                    CREATE TABLE IF NOT EXISTS feedback (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        message_id BIGINT NOT NULL,
                        session_id VARCHAR(255) NOT NULL,
                        user_id VARCHAR(255) NOT NULL,
                        rating INT NOT NULL,
                        comment TEXT,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_message_id (message_id),
                        INDEX idx_session_id (session_id),
                        INDEX idx_user_id (user_id),
                        INDEX idx_rating (rating),
                        INDEX idx_created_at (created_at)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """
                    await cursor.execute(create_feedback_table_sql)
                    
                    # 修改已存在表的message_id字段类型为BIGINT
                    alter_table_sql = """
                    ALTER TABLE feedback MODIFY COLUMN message_id BIGINT NOT NULL
                    """
                    try:
                        await cursor.execute(alter_table_sql)
                    except Exception as e:
                        # 如果表不存在或字段类型已经是BIGINT，忽略错误
                        logger.debug(f"修改feedback表结构失败（可能已存在或字段类型已正确）: {e}")
                    
                    # 插入反馈数据
                    insert_sql = """
                    INSERT INTO feedback (message_id, session_id, user_id, rating, comment)
                    VALUES (%s, %s, %s, %s, %s)
                    """
                    
                    await cursor.execute(insert_sql, (
                        message_id, session_id, user_id, rating, comment
                    ))
                    
                    logger.info(f"保存反馈成功: 消息ID {message_id}, 评分 {rating}")
                    return True
                    
        except Exception as e:
            logger.error(f"保存反馈失败: {e}")
            return False
    
    async def get_low_rating_feedbacks(self, days: int = 7) -> List[Dict]:
        """
        获取低评分反馈
        
        Args:
            days: 天数范围
            
        Returns:
            低评分反馈列表
        """
        if not self.connection_pool:
            return []
        
        try:
            async with self.connection_pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cursor:
                    select_sql = """
                    SELECT f.*, c.content as message_content
                    FROM feedback f
                    JOIN chat_messages c ON f.message_id = c.id
                    WHERE f.rating < 3
                    AND f.created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                    ORDER BY f.created_at DESC
                    """
                    
                    await cursor.execute(select_sql, (days,))
                    results = await cursor.fetchall()
                    
                    logger.info(f"获取低评分反馈: {len(results)} 条")
                    return results
                    
        except Exception as e:
            logger.error(f"获取低评分反馈失败: {e}")
            return []

# 全局MySQL管理器实例
mysql_manager = MySQLManager()