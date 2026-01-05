import os
from typing import Optional
from pydantic import BaseModel

class Settings(BaseModel):
    """应用配置"""
    app_name: str = "客服系统Demo API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # JWT配置
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # 数据库配置
    mysql_host: str = os.getenv("MYSQL_HOST", "localhost")
    mysql_port: int = int(os.getenv("MYSQL_PORT", "3306"))
    mysql_user: str = os.getenv("MYSQL_USER", "root")
    mysql_password: str = os.getenv("MYSQL_PASSWORD", "011216")
    mysql_database: str = os.getenv("MYSQL_DATABASE", "customer")
    
    # Redis配置
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_password: Optional[str] = os.getenv("REDIS_PASSWORD")
    redis_db: int = int(os.getenv("REDIS_DB", "0"))
    
    # ChromaDB配置
    chroma_db_path: str = os.getenv("CHROMA_DB_PATH", "./chroma_db")

# 创建全局配置实例
settings = Settings()