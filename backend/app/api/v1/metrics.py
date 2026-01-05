"""
Prometheus 指标 API 端点
"""
from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse
import logging

from app.managers.prometheus_manager import prometheus_metrics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])

@router.get("/", response_class=PlainTextResponse)
async def get_prometheus_metrics():
    """
    获取 Prometheus 指标数据
    
    这个端点会被 Prometheus 服务器定期抓取
    """
    try:
        metrics_data = prometheus_metrics.get_metrics()
        logger.debug("Prometheus 指标数据已生成")
        return Response(
            content=metrics_data,
            media_type=prometheus_metrics.get_content_type()
        )
    except Exception as e:
        logger.error(f"生成 Prometheus 指标失败: {e}")
        return Response(
            content=f"# Error generating metrics: {str(e)}",
            media_type="text/plain",
            status_code=500
        )

@router.get("/health")
async def metrics_health_check():
    """
    指标系统健康检查
    """
    return {
        "status": "healthy",
        "metrics_available": True,
        "timestamp": prometheus_metrics.get_metrics() is not None
    }
