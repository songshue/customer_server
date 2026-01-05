"""
Prometheus 指标管理器
负责收集和暴露系统监控指标
"""
import time
from typing import Dict, Any
from prometheus_client import (
    Counter, Histogram, Gauge, CollectorRegistry,
    generate_latest, CONTENT_TYPE_LATEST,
    Info, Enum
)
import psutil
import logging
from datetime import datetime
import json
from contextlib import contextmanager

# 自定义指标收集器
class PrometheusMetrics:
    def __init__(self):
        self.registry = CollectorRegistry()
        
        # ==================== API 性能指标 ====================
        # HTTP 请求计数器
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total number of HTTP requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )
        
        # HTTP 请求耗时直方图
        self.http_request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        # ==================== WebSocket 指标 ====================
        # WebSocket 连接数
        self.websocket_connections = Gauge(
            'websocket_connections_active',
            'Number of active WebSocket connections',
            registry=self.registry
        )
        
        # WebSocket 消息计数器
        self.websocket_messages_total = Counter(
            'websocket_messages_total',
            'Total number of WebSocket messages',
            ['message_type', 'direction'],
            registry=self.registry
        )
        
        # ==================== 数据库指标 ====================
        # 数据库查询计时器
        self.db_query_duration = Histogram(
            'db_query_duration_seconds',
            'Database query duration in seconds',
            ['operation', 'table'],
            registry=self.registry
        )
        
        # 数据库连接池状态
        self.db_connections_active = Gauge(
            'db_connections_active',
            'Number of active database connections',
            registry=self.registry
        )
        
        # ==================== Redis 指标 ====================
        # Redis 操作计时器
        self.redis_operation_duration = Histogram(
            'redis_operation_duration_seconds',
            'Redis operation duration in seconds',
            ['operation', 'status'],
            registry=self.registry
        )
        
        # Redis 缓存命中率
        self.redis_cache_hits = Counter(
            'redis_cache_hits_total',
            'Total number of Redis cache hits',
            ['operation'],
            registry=self.registry
        )
        
        self.redis_cache_misses = Counter(
            'redis_cache_misses_total',
            'Total number of Redis cache misses',
            ['operation'],
            registry=self.registry
        )
        
        # ==================== 聊天会话指标 ====================
        # 活跃会话数
        self.active_sessions = Gauge(
            'chat_sessions_active',
            'Number of active chat sessions',
            registry=self.registry
        )
        
        # 总会话数
        self.total_sessions = Counter(
            'chat_sessions_total',
            'Total number of chat sessions created',
            ['user_type'],
            registry=self.registry
        )
        
        # 消息计数器
        self.chat_messages_total = Counter(
            'chat_messages_total',
            'Total number of chat messages',
            ['role', 'session_type'],
            registry=self.registry
        )
        
        # 聊天API错误计数器
        self.chat_api_errors_total = Counter(
            'chat_api_errors_total',
            'Total number of chat API errors',
            ['error_type'],
            registry=self.registry
        )
        
        # ==================== 系统性能指标 ====================
        # CPU 使用率
        self.cpu_usage_percent = Gauge(
            'system_cpu_usage_percent',
            'CPU usage percentage',
            registry=self.registry
        )
        
        # 内存使用量
        self.memory_usage_bytes = Gauge(
            'system_memory_usage_bytes',
            'Memory usage in bytes',
            ['type'],
            registry=self.registry
        )
        
        # 磁盘使用率
        self.disk_usage_percent = Gauge(
            'system_disk_usage_percent',
            'Disk usage percentage',
            ['mountpoint'],
            registry=self.registry
        )
        
        # 网络IO
        self.network_bytes_sent = Counter(
            'system_network_bytes_sent_total',
            'Total network bytes sent',
            registry=self.registry
        )
        
        self.network_bytes_recv = Counter(
            'system_network_bytes_recv_total',
            'Total network bytes received',
            registry=self.registry
        )
        
        # ==================== RAG 指标 ====================
        # RAG 查询计数
        self.rag_queries_total = Counter(
            'rag_queries_total',
            'Total number of RAG queries',
            ['result_type'],
            registry=self.registry
        )
        
        # RAG 查询耗时
        self.rag_query_duration = Histogram(
            'rag_query_duration_seconds',
            'RAG query duration in seconds',
            registry=self.registry
        )
        
        # RAG 检索文档数
        self.rag_retrieved_docs = Histogram(
            'rag_retrieved_docs_count',
            'Number of documents retrieved in RAG queries',
            registry=self.registry
        )
        
        # ==================== 认证指标 ====================
        # 登录尝试次数
        self.login_attempts_total = Counter(
            'auth_login_attempts_total',
            'Total number of login attempts',
            ['status'],
            registry=self.registry
        )
        
        # JWT 令牌相关指标
        self.jwt_tokens_issued_total = Counter(
            'auth_jwt_tokens_issued_total',
            'Total number of JWT tokens issued',
            ['token_type'],
            registry=self.registry
        )
        
        self.jwt_tokens_revoked_total = Counter(
            'auth_jwt_tokens_revoked_total',
            'Total number of JWT tokens revoked',
            ['reason'],
            registry=self.registry
        )
        
        # ==================== 应用信息 ====================
        self.app_info = Info(
            'app_info',
            'Application information',
            registry=self.registry
        )
        
        # 设置应用信息
        self.app_info.info({
            'version': '1.0.0',
            'environment': 'production',
            'build_time': datetime.now().isoformat(),
            'name': 'Customer Service Chat Backend'
        })
        
        # 系统状态枚举
        self.system_status = Enum(
            'system_status',
            'System status',
            ['component'],
            states=['healthy', 'degraded', 'unhealthy'],
            registry=self.registry
        )
        
        # 初始化系统状态
        self.update_system_metrics()
    
    def update_system_metrics(self):
        """更新系统性能指标"""
        try:
            # CPU 使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            self.cpu_usage_percent.set(cpu_percent)
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            self.memory_usage_bytes.labels(type='total').set(memory.total)
            self.memory_usage_bytes.labels(type='available').set(memory.available)
            self.memory_usage_bytes.labels(type='used').set(memory.used)
            self.memory_usage_bytes.labels(type='free').set(memory.free)
            
            # 磁盘使用情况
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    self.disk_usage_percent.labels(mountpoint=partition.mountpoint).set(
                        (usage.used / usage.total) * 100
                    )
                except (PermissionError, OSError):
                    continue
            
            # 网络IO
            network = psutil.net_io_counters()
            self.network_bytes_sent.inc(network.bytes_sent)
            self.network_bytes_recv.inc(network.bytes_recv)
            
            # 更新系统状态
            if cpu_percent < 80 and memory.percent < 85:
                self.system_status.labels(component='overall').state('healthy')
            elif cpu_percent < 95 and memory.percent < 95:
                self.system_status.labels(component='overall').state('degraded')
            else:
                self.system_status.labels(component='overall').state('unhealthy')
                
        except Exception as e:
            logging.error(f"更新系统指标失败: {e}")
    
    @contextmanager
    def timer(self, metric: Histogram, labels: Dict[str, str] = None):
        """性能计时器上下文管理器"""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            if labels:
                metric.labels(**labels).observe(duration)
            else:
                metric.observe(duration)
    
    def increment_counter(self, counter: Counter, amount: int = 1, labels: Dict[str, str] = None):
        """增加计数器"""
        if labels:
            counter.labels(**labels).inc(amount)
        else:
            counter.inc(amount)
    
    def set_gauge(self, gauge: Gauge, value: float, labels: Dict[str, str] = None):
        """设置Gauge值"""
        if labels:
            gauge.labels(**labels).set(value)
        else:
            gauge.set(value)
    
    def get_metrics(self) -> str:
        """获取所有指标的文本格式"""
        return generate_latest(self.registry).decode('utf-8')
    
    def get_content_type(self) -> str:
        """获取指标响应的Content-Type"""
        return CONTENT_TYPE_LATEST
    
    def record_api_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """记录API请求"""
        self.http_requests_total.labels(
            method=method.upper(),
            endpoint=endpoint,
            status_code=status_code
        ).inc()
        
        self.http_request_duration.labels(
            method=method.upper(),
            endpoint=endpoint
        ).observe(duration)
    
    def record_websocket_event(self, event_type: str, direction: str = None):
        """记录WebSocket事件"""
        self.websocket_messages_total.labels(
            message_type=event_type,
            direction=direction or 'unknown'
        ).inc()
    
    def update_active_connections(self, count: int):
        """更新活跃WebSocket连接数"""
        self.websocket_connections.set(count)
    
    def update_active_sessions(self, count: int):
        """更新活跃会话数"""
        self.active_sessions.set(count)
    
    def record_db_operation(self, operation: str, table: str, duration: float):
        """记录数据库操作"""
        self.db_query_duration.labels(
            operation=operation,
            table=table
        ).observe(duration)
    
    def record_redis_operation(self, operation: str, duration: float, success: bool = True):
        """记录Redis操作"""
        self.redis_operation_duration.labels(
            operation=operation,
            status='success' if success else 'error'
        ).observe(duration)
    
    def record_cache_hit(self, operation: str, hit: bool = True):
        """记录缓存命中/未命中"""
        if hit:
            self.redis_cache_hits.labels(operation=operation).inc()
        else:
            self.redis_cache_misses.labels(operation=operation).inc()
    
    def record_chat_session(self, user_type: str = 'regular', active_count: int = 0):
        """记录聊天会话"""
        self.total_sessions.labels(user_type=user_type).inc()
        self.active_sessions.set(active_count)
    
    def record_chat_message(self, role: str, session_type: str = 'regular'):
        """记录聊天消息"""
        self.chat_messages_total.labels(role=role, session_type=session_type).inc()
    
    def record_rag_query(self, duration: float, doc_count: int, has_references: bool):
        """记录RAG查询"""
        self.rag_queries_total.labels(
            result_type='with_references' if has_references else 'no_references'
        ).inc()
        
        self.rag_query_duration.observe(duration)
        self.rag_retrieved_docs.observe(doc_count)
    
    def record_auth_event(self, event_type: str, status: str = None, **labels):
        """记录认证事件"""
        if event_type == 'login_attempt':
            if status is None:
                status = 'unknown'
            self.login_attempts_total.labels(status=status).inc()
        elif event_type == 'jwt_issued':
            token_type = labels.get('token_type', 'unknown')
            self.jwt_tokens_issued_total.labels(token_type=token_type).inc()
        elif event_type == 'jwt_revoked':
            reason = labels.get('reason', 'unknown')
            self.jwt_tokens_revoked_total.labels(reason=reason).inc()
    
    def record_chat_event(self, event_type: str, **labels):
        """记录聊天事件"""
        if event_type == 'session_creation_api_failed':
            self.chat_api_errors_total.labels(error_type='session_creation').inc()
        elif event_type == 'session_retrieval_failed':
            self.chat_api_errors_total.labels(error_type='session_retrieval').inc()
        elif event_type == 'session_deletion_failed':
            self.chat_api_errors_total.labels(error_type='session_deletion').inc()
        elif event_type == 'session_rename_failed':
            self.chat_api_errors_total.labels(error_type='session_rename').inc()
        elif event_type == 'chat_message_processing_failed':
            self.chat_api_errors_total.labels(error_type='message_processing').inc()
        elif event_type == 'websocket_connection_failed':
            self.chat_api_errors_total.labels(error_type='websocket_connection').inc()
        elif event_type == 'message_sent':
            # 记录消息发送事件
            pass
        elif event_type == 'http_chat_request':
            # 记录HTTP聊天请求事件
            pass
        elif event_type == 'user_message_received':
            # 记录用户消息接收事件
            pass
    
    def record_chat_message_size(self, size: int):
        """记录聊天消息大小"""
        # 这里可以添加消息大小分布的直方图
        # 暂时使用日志记录，后续可以添加更详细的指标
        logging.debug(f"消息大小: {size} 字节")
        
    def record_websocket_message(self, message_type: str, size: int = 0):
        """记录WebSocket消息"""
        self.websocket_messages_total.labels(
            message_type=message_type,
            direction='sent' if message_type in ['connected', 'message', 'heartbeat'] else 'received'
        ).inc()

# 全局指标管理器实例
prometheus_metrics = PrometheusMetrics()
