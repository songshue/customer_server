import os
import sys
import logging
import asyncio
from datetime import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.api.v1 import auth, chat, metrics, knowledge, feedback
from app.managers.redis_manager import redis_manager
from app.managers.mysql_manager import mysql_manager
from app.managers.prometheus_manager import prometheus_metrics
from app.middleware.prometheus_middleware import PrometheusMiddleware
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    description="基于FastAPI的智能客服系统",
    version=settings.app_version
)

app.add_middleware(PrometheusMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api", tags=["认证"])
app.include_router(chat.router, prefix="/api/v1", tags=["聊天"])
app.include_router(feedback.router, prefix="/api/v1", tags=["反馈"])
app.include_router(metrics.router, prefix="/api/v1/metrics", tags=["指标"])
app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["知识库"])

@app.on_event("startup")
async def startup():
    try:
        await redis_manager.connect()
        await mysql_manager.connect()
        logger.info("数据库连接初始化成功")
    except Exception as e:
        logger.error(f"数据库连接初始化失败: {e}")

@app.get("/")
async def root():
    return {
        "message": "客服系统Demo API正在运行", 
        "status": "ok",
        "version": settings.app_version
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
