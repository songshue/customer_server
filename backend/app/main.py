import os
import sys
import logging
import asyncio
from datetime import datetime

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.api.v1 import auth, chat, metrics
from app.managers.redis_manager import redis_manager
from app.managers.mysql_manager import mysql_manager
from app.managers.prometheus_manager import prometheus_metrics
from app.middleware.prometheus_middleware import PrometheusMiddleware
from app.core.config import settings

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    description="基于FastAPI的智能客服系统",
    version=settings.app_version
)

# 添加Prometheus指标中间件
app.add_middleware(PrometheusMiddleware)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册API路由
app.include_router(auth.router, prefix="/api", tags=["认证"])
app.include_router(chat.router, prefix="/api/v1", tags=["聊天"])
app.include_router(metrics.router, prefix="/api/v1/metrics", tags=["指标"])

@app.on_event("startup")
async def startup():
    """应用启动事件"""
    try:
        await redis_manager.connect()
        await mysql_manager.connect()
        logger.info("数据库连接初始化成功")
    except Exception as e:
        logger.error(f"数据库连接初始化失败: {e}")

@app.get("/")
async def root():
    """根路径检查"""
    return {
        "message": "客服系统Demo API正在运行", 
        "status": "ok",
        "version": settings.app_version
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )