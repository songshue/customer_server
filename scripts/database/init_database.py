#!/usr/bin/env python3
"""
数据库初始化脚本
创建用户、聊天会话、消息等数据表
"""
import asyncio
import os
import logging
from datetime import datetime
import aiomysql

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 数据库配置
DB_CONFIG = {
    'host': os.getenv("MYSQL_HOST", "localhost"),
    'port': int(os.getenv("MYSQL_PORT", "3306")),
    'user': os.getenv("MYSQL_USER", "root"),
    'password': os.getenv("MYSQL_PASSWORD", "011216"),
    'charset': 'utf8mb4',
    'autocommit': True
}

DATABASE_NAME = os.getenv("MYSQL_DATABASE", "customer")

# SQL 创建表语句
CREATE_DATABASE_SQL = f"""
CREATE DATABASE IF NOT EXISTS {DATABASE_NAME} 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;
"""

CREATE_TABLES_SQL = f"""
USE {DATABASE_NAME};

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    INDEX idx_username (username),
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 聊天会话表
CREATE TABLE IF NOT EXISTS chat_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    user_id VARCHAR(255) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active',
    metadata TEXT NULL,
    INDEX idx_session_id (session_id),
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 聊天消息表
CREATE TABLE IF NOT EXISTS chat_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    role ENUM('user', 'assistant') NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR(255) NULL,
    metadata TEXT NULL,
    INDEX idx_session_id (session_id),
    INDEX idx_user_id (user_id),
    INDEX idx_timestamp (timestamp),
    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 用户反馈表
CREATE TABLE IF NOT EXISTS user_feedback (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    message_id INT NULL,
    user_id VARCHAR(255) NULL,
    feedback_type VARCHAR(20) NOT NULL,
    rating INT NULL,
    comment TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT NULL,
    INDEX idx_session_id (session_id),
    INDEX idx_message_id (message_id),
    INDEX idx_user_id (user_id),
    INDEX idx_feedback_type (feedback_type),
    FOREIGN KEY (session_id) REFERENCES chat_sessions(session_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建默认管理员用户
INSERT IGNORE INTO users (username, email, hashed_password) 
VALUES ('admin', 'admin@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj8X3JqL.5mS');

-- 创建一些示例数据
INSERT IGNORE INTO chat_sessions (session_id, user_id, status) 
VALUES ('demo-session-1', 'demo-user', 'active');

INSERT IGNORE INTO chat_messages (session_id, role, content, user_id)
VALUES 
    ('demo-session-1', 'user', '你好，这是一个示例对话', 'demo-user'),
    ('demo-session-1', 'assistant', '您好！我是客服助手，很高兴为您服务。有什么我可以帮助您的吗？', NULL);
"""

async def create_database():
    """创建数据库"""
    try:
        # 连接MySQL服务器（不指定数据库）
        conn = await aiomysql.connect(**DB_CONFIG)
        async with conn.cursor() as cursor:
            await cursor.execute(CREATE_DATABASE_SQL)
            logger.info(f"数据库 {DATABASE_NAME} 创建成功或已存在")
        conn.close()
        return True
    except Exception as e:
        logger.error(f"创建数据库失败: {e}")
        return False

async def create_tables():
    """创建数据表"""
    try:
        # 添加数据库名称到连接配置
        db_config_with_db = DB_CONFIG.copy()
        db_config_with_db['db'] = DATABASE_NAME
        
        conn = await aiomysql.connect(**db_config_with_db)
        async with conn.cursor() as cursor:
            # 执行建表SQL
            for statement in CREATE_TABLES_SQL.split(';'):
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    await cursor.execute(statement)
            
            logger.info("数据表创建成功")
        conn.close()
        return True
    except Exception as e:
        logger.error(f"创建数据表失败: {e}")
        return False

async def verify_tables():
    """验证数据表是否创建成功"""
    try:
        db_config_with_db = DB_CONFIG.copy()
        db_config_with_db['db'] = DATABASE_NAME
        
        conn = await aiomysql.connect(**db_config_with_db)
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute("SHOW TABLES")
            tables = await cursor.fetchall()
            
            expected_tables = ['users', 'chat_sessions', 'chat_messages', 'user_feedback']
            found_tables = [list(table.values())[0] for table in tables]
            
            logger.info(f"找到的数据表: {found_tables}")
            
            for table in expected_tables:
                if table in found_tables:
                    logger.info(f"✓ {table} 表存在")
                else:
                    logger.warning(f"✗ {table} 表不存在")
                    
        conn.close()
        return True
    except Exception as e:
        logger.error(f"验证数据表失败: {e}")
        return False

async def main():
    """主函数"""
    logger.info("开始初始化数据库...")
    
    # 检查数据库连接
    try:
        # 先测试连接
        temp_config = DB_CONFIG.copy()
        temp_config['db'] = 'mysql'  # 连接到MySQL系统数据库
        conn = await aiomysql.connect(**temp_config)
        await conn.ping()
        conn.close()
        logger.info("✓ 数据库连接正常")
    except Exception as e:
        logger.error(f"✗ 数据库连接失败: {e}")
        return
    
    # 创建数据库
    if await create_database():
        logger.info("✓ 数据库创建完成")
    else:
        logger.error("✗ 数据库创建失败")
        return
    
    # 创建数据表
    if await create_tables():
        logger.info("✓ 数据表创建完成")
    else:
        logger.error("✗ 数据表创建失败")
        return
    
    # 验证数据表
    if await verify_tables():
        logger.info("✓ 数据表验证完成")
    else:
        logger.warning("⚠ 数据表验证失败")
    
    logger.info("数据库初始化完成！")

if __name__ == "__main__":
    asyncio.run(main())