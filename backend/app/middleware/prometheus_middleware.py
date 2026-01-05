"""
FastAPI 中间件 - 用于记录 API 性能和错误指标
"""
import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from app.managers.prometheus_manager import prometheus_metrics

logger = logging.getLogger(__name__)

class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Prometheus 指标中间件
    记录 HTTP 请求的指标数据
    """
    
    def __init__(self, app, exclude_paths: set = None):
        super().__init__(app)
        # 排除的路径（不记录指标）
        self.exclude_paths = exclude_paths or {
            '/metrics',  # Prometheus 指标端点
            '/health',   # 健康检查端点
            '/docs',     # API 文档
            '/redoc',    # ReDoc 文档
            '/openapi.json'  # OpenAPI 规范
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 检查是否应该排除这个路径
        if request.url.path in self.exclude_paths:
            return await call_next(request)
        
        # 记录请求开始时间
        start_time = time.time()
        
        # 获取请求信息
        method = request.method
        endpoint = self._normalize_endpoint(request.url.path)
        
        try:
            # 处理请求
            response = await call_next(request)
            
            # 计算请求耗时
            duration = time.time() - start_time
            
            # 记录指标
            prometheus_metrics.record_api_request(
                method=method,
                endpoint=endpoint,
                status_code=response.status_code,
                duration=duration
            )
            
            logger.debug(f"API请求: {method} {endpoint} - {response.status_code} - {duration:.3f}s")
            
            return response
            
        except Exception as e:
            # 记录错误
            duration = time.time() - start_time
            error_status_code = 500
            
            prometheus_metrics.record_api_request(
                method=method,
                endpoint=endpoint,
                status_code=error_status_code,
                duration=duration
            )
            
            logger.error(f"API请求异常: {method} {endpoint} - {duration:.3f}s - {str(e)}")
            
            # 重新抛出异常
            raise
    
    def _normalize_endpoint(self, path: str) -> str:
        """
        规范化端点路径，将动态参数转换为占位符
        例如: /users/123 -> /users/{id}
        """
        # 简单的路径规范化
        parts = path.split('/')
        normalized_parts = []
        
        for part in parts:
            if part.isdigit() or len(part) == 36:  # UUID 长度
                normalized_parts.append('{id}')
            else:
                normalized_parts.append(part)
        
        return '/'.join(normalized_parts)

class WebSocketMetricsMiddleware:
    """
    WebSocket 指标中间件
    记录 WebSocket 连接和消息指标
    """
    
    def __init__(self):
        self.active_connections = 0
    
    def connection_opened(self):
        """WebSocket 连接建立"""
        self.active_connections += 1
        prometheus_metrics.set_gauge(
            prometheus_metrics.websocket_connections,
            self.active_connections
        )
        logger.debug(f"WebSocket连接建立，当前活跃连接数: {self.active_connections}")
    
    def connection_closed(self):
        """WebSocket 连接关闭"""
        self.active_connections = max(0, self.active_connections - 1)
        prometheus_metrics.set_gauge(
            prometheus_metrics.websocket_connections,
            self.active_connections
        )
        logger.debug(f"WebSocket连接关闭，当前活跃连接数: {self.active_connections}")
    
    def message_sent(self, message_type: str = "unknown"):
        """记录发送的消息"""
        prometheus_metrics.record_websocket_event(
            event_type=message_type,
            direction="sent"
        )
    
    def message_received(self, message_type: str = "unknown"):
        """记录接收的消息"""
        prometheus_metrics.record_websocket_event(
            event_type=message_type,
            direction="received"
        )

# 全局 WebSocket 指标中间件实例
websocket_metrics = WebSocketMetricsMiddleware()
