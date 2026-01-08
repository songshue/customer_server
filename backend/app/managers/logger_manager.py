"""
日志记录管理器
记录聊天对话、系统事件等日志信息 - 使用结构化日志输出
"""
import os
import logging
import sys
from datetime import datetime
from typing import Dict, Optional
import json
import asyncio
import structlog
from pathlib import Path
from pythonjsonlogger import jsonlogger

class LoggerManager:
    def __init__(self):
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # 配置结构化日志
        self._setup_structured_logging()
        
        # 获取structlog记录器
        self.logger = structlog.get_logger()
        self.chat_logger = structlog.get_logger("chat")
        self.system_logger = structlog.get_logger("system")
        self.performance_logger = structlog.get_logger("performance")
        
    def _setup_structured_logging(self):
        """设置结构化日志配置"""
        # 清除现有的handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        # 创建JSON格式化器，便于Loki收集
        class LokiJSONFormatter(jsonlogger.JsonFormatter):
            def add_fields(self, log_record, record, message_dict):
                super().add_fields(log_record, record, message_dict)
                if not log_record.get('timestamp'):
                    log_record['timestamp'] = datetime.now().isoformat()
                if log_record.get('level'):
                    log_record['level'] = log_record['level'].upper()
                else:
                    log_record['level'] = record.levelname
        
        # 创建格式化器
        json_formatter = LokiJSONFormatter(
            '%(timestamp)s %(levelname)s %(name)s %(message)s',
            rename_fields={'levelname': 'level', 'name': 'logger'}
        )
        
        file_formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        console_formatter = LokiJSONFormatter(
            '%(timestamp)s %(levelname)s %(name)s %(message)s',
            rename_fields={'levelname': 'level', 'name': 'logger'}
        )
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.INFO)
        
        # 文件处理器 - 同时输出JSON格式到文件，便于Loki收集
        chat_handler = logging.FileHandler(self.log_dir / "chat.log", encoding='utf-8')
        chat_handler.setFormatter(json_formatter)
        chat_handler.setLevel(logging.INFO)
        
        system_handler = logging.FileHandler(self.log_dir / "system.log", encoding='utf-8')
        system_handler.setFormatter(json_formatter)
        system_handler.setLevel(logging.INFO)
        
        performance_handler = logging.FileHandler(self.log_dir / "performance.log", encoding='utf-8')
        performance_handler.setFormatter(json_formatter)
        performance_handler.setLevel(logging.INFO)
        
        # 配置根记录器（只保留控制台输出用于重要信息）
        root_logger.setLevel(logging.WARNING)  # 只输出WARNING及以上级别到控制台
        root_logger.addHandler(console_handler)
        
        # 配置各个子记录器
        chat_logger = logging.getLogger("chat")
        chat_logger.addHandler(chat_handler)
        chat_logger.setLevel(logging.INFO)
        chat_logger.propagate = False  # 防止日志向上传播到根记录器
        
        system_logger = logging.getLogger("system")
        system_logger.addHandler(system_handler)
        system_logger.setLevel(logging.INFO)
        system_logger.propagate = False
        
        performance_logger = logging.getLogger("performance")
        performance_logger.addHandler(performance_handler)
        performance_logger.setLevel(logging.INFO)
        performance_logger.propagate = False
        
        # 配置structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    
    async def log_chat_message(self, session_id: str, user_id: str, role: str, content: str, 
                             metadata: Optional[Dict] = None, trace_id: str = None):
        """
        记录聊天消息
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            role: 消息角色 (user/assistant)
            content: 消息内容
            metadata: 额外元数据
            trace_id: 跟踪ID，用于日志关联
        """
        try:
            timestamp = datetime.now()
            
            # 准备结构化日志数据
            log_data = {
                "timestamp": timestamp.isoformat(),
                "session_id": session_id,
                "user_id": user_id,
                "role": role,
                "content": content,
                "content_length": len(content),
                "metadata": metadata or {},
                "trace_id": trace_id
            }
            
            # 根据角色选择不同的日志级别和格式
            if role == "user":
                self.chat_logger.info(
                    "user_message",
                    **log_data
                )
            else:
                self.chat_logger.info(
                    "assistant_message", 
                    **log_data
                )
            
        except Exception as e:
            self.logger.error("记录聊天消息失败", error=str(e), session_id=session_id, user_id=user_id)
    
    async def log_conversation(self, session_id: str, user_id: str, conversation_data: Dict, trace_id: str = None):
        """记录完整对话"""
        try:
            timestamp = datetime.now()
            
            log_data = {
                "timestamp": timestamp.isoformat(),
                "session_id": session_id,
                "user_id": user_id,
                "conversation_length": len(conversation_data.get("messages", [])),
                "conversation_summary": {
                    "total_messages": len(conversation_data.get("messages", [])),
                    "user_messages": len([m for m in conversation_data.get("messages", []) if m.get("role") == "user"]),
                    "ai_messages": len([m for m in conversation_data.get("messages", []) if m.get("role") == "assistant"])
                },
                "trace_id": trace_id
            }
            
            self.chat_logger.info("conversation_recorded", **log_data)
            
        except Exception as e:
            self.logger.error("记录对话失败", error=str(e), session_id=session_id)
    
    async def log_chat_event(self, event_type: str, session_id: str = None, user_id: str = None, 
                           message_content: str = None, duration: float = None, trace_id: str = None):
        """记录聊天事件"""
        try:
            timestamp = datetime.now()
            
            log_data = {
                "timestamp": timestamp.isoformat(),
                "event_type": event_type,
                "session_id": session_id,
                "user_id": user_id,
                "message_content": message_content,
                "duration": duration,
                "trace_id": trace_id
            }
            
            self.chat_logger.info("chat_event", **log_data)
            
        except Exception as e:
            self.logger.error("记录聊天事件失败", error=str(e), event_type=event_type)
    
    async def log_system_event(self, event_type: str, message: str, details: Optional[Dict] = None, trace_id: str = None):
        """记录系统事件"""
        try:
            timestamp = datetime.now()
            
            log_data = {
                "timestamp": timestamp.isoformat(),
                "event_type": event_type,
                "message": message,
                "details": details or {},
                "trace_id": trace_id
            }
            
            self.system_logger.info("system_event", **log_data)
            
        except Exception as e:
            self.logger.error("记录系统事件失败", error=str(e), event_type=event_type)
    
    async def log_error(self, error_type: str, error_message: str, context: Optional[Dict] = None, trace_id: str = None):
        """记录错误"""
        try:
            timestamp = datetime.now()
            
            log_data = {
                "timestamp": timestamp.isoformat(),
                "error_type": error_type,
                "error_message": error_message,
                "context": context or {},
                "trace_id": trace_id
            }
            
            self.system_logger.error("system_error", **log_data)
            
        except Exception as e:
            self.logger.error("记录错误日志失败", error=str(e))
    
    async def log_performance(self, operation: str, duration: float, details: Optional[Dict] = None, trace_id: str = None):
        """记录性能信息"""
        try:
            timestamp = datetime.now()
            
            log_data = {
                "timestamp": timestamp.isoformat(),
                "operation": operation,
                "duration": duration,
                "duration_ms": duration * 1000,
                "details": details or {},
                "trace_id": trace_id
            }
            
            # 根据性能表现设置不同级别
            if duration > 5.0:  # 超过5秒的慢操作
                self.performance_logger.warning("slow_operation", **log_data)
            else:
                self.performance_logger.info("performance_metric", **log_data)
            
        except Exception as e:
            self.logger.error("记录性能日志失败", error=str(e))
    
    async def log_rag_query(self, session_id: str, query: str, retrieved_docs: int, 
                           processing_time: float, has_references: bool, trace_id: str = None):
        """记录RAG查询信息"""
        try:
            timestamp = datetime.now()
            
            log_data = {
                "timestamp": timestamp.isoformat(),
                "session_id": session_id,
                "query_length": len(query),
                "query_preview": query[:100] + "..." if len(query) > 100 else query,
                "retrieved_docs": retrieved_docs,
                "processing_time": processing_time,
                "processing_time_ms": processing_time * 1000,
                "has_references": has_references,
                "efficiency_score": retrieved_docs / processing_time if processing_time > 0 else 0,
                "trace_id": trace_id
            }
            
            self.performance_logger.info("rag_query", **log_data)
            
        except Exception as e:
            self.logger.error("记录RAG查询失败", error=str(e), session_id=session_id)
    
    async def log_api_request(self, method: str, endpoint: str, status_code: int, 
                            duration: float, user_id: str = None, trace_id: str = None):
        """记录API请求"""
        try:
            timestamp = datetime.now()
            
            log_data = {
                "timestamp": timestamp.isoformat(),
                "method": method,
                "endpoint": endpoint,
                "status_code": status_code,
                "duration": duration,
                "duration_ms": duration * 1000,
                "user_id": user_id,
                "success": 200 <= status_code < 400,
                "trace_id": trace_id
            }
            
            if 200 <= status_code < 300:
                self.system_logger.info("api_request_success", **log_data)
            elif 300 <= status_code < 400:
                self.system_logger.info("api_request_redirect", **log_data)
            elif 400 <= status_code < 500:
                self.system_logger.warning("api_request_client_error", **log_data)
            else:
                self.system_logger.error("api_request_server_error", **log_data)
            
        except Exception as e:
            self.logger.error("记录API请求失败", error=str(e))
    
    async def log_database_operation(self, operation: str, table: str, duration: float, 
                                   success: bool, rows_affected: int = 0, trace_id: str = None):
        """记录数据库操作"""
        try:
            timestamp = datetime.now()
            
            log_data = {
                "timestamp": timestamp.isoformat(),
                "operation": operation,
                "table": table,
                "duration": duration,
                "duration_ms": duration * 1000,
                "success": success,
                "rows_affected": rows_affected,
                "trace_id": trace_id
            }
            
            if success:
                self.performance_logger.info("database_operation", **log_data)
            else:
                self.performance_logger.error("database_operation_failed", **log_data)
            
        except Exception as e:
            self.logger.error("记录数据库操作失败", error=str(e))
    
    async def log_websocket_event(self, session_id: str, event_type: str, 
                                user_id: str = None, message_size: int = 0, trace_id: str = None):
        """记录WebSocket事件"""
        try:
            timestamp = datetime.now()
            
            log_data = {
                "timestamp": timestamp.isoformat(),
                "session_id": session_id,
                "event_type": event_type,
                "user_id": user_id,
                "message_size": message_size,
                "trace_id": trace_id
            }
            
            self.system_logger.info("websocket_event", **log_data)
            
        except Exception as e:
            self.logger.error("记录WebSocket事件失败", error=str(e))
    
    async def log_auth_event(self, event_type: str, username: str = None, 
                           success: bool = True, details: Optional[Dict] = None, trace_id: str = None):
        """记录认证事件"""
        try:
            timestamp = datetime.now()
            
            log_data = {
                "timestamp": timestamp.isoformat(),
                "event_type": event_type,
                "username": username,
                "success": success,
                "details": details or {},
                "trace_id": trace_id
            }
            
            if success:
                self.system_logger.info("auth_event_success", **log_data)
            else:
                self.system_logger.warning("auth_event_failure", **log_data)
            
        except Exception as e:
            self.logger.error("记录认证事件失败", error=str(e))
    
    async def get_chat_logs(self, session_id: Optional[str] = None, limit: int = 100) -> list:
        """获取聊天日志"""
        try:
            # 这里可以从结构化日志文件中读取
            # 暂时返回空列表，实际实现中需要配置文件输出
            return []
            
        except Exception as e:
            self.logger.error("获取聊天日志失败", error=str(e))
            return []
    
    async def get_session_summary(self, session_id: str) -> Dict:
        """获取会话摘要"""
        try:
            logs = await self.get_chat_logs(session_id)
            
            user_messages = [log for log in logs if log.get('role') == 'user']
            ai_messages = [log for log in logs if log.get('role') == 'assistant']
            
            summary = {
                "session_id": session_id,
                "total_messages": len(logs),
                "user_messages": len(user_messages),
                "ai_messages": len(ai_messages),
                "first_message_time": logs[0]['timestamp'] if logs else None,
                "last_message_time": logs[-1]['timestamp'] if logs else None,
                "user_questions": [msg['content'] for msg in user_messages[-3:]]  # 最近3个问题
            }
            
            return summary
            
        except Exception as e:
            self.logger.error("获取会话摘要失败", error=str(e), session_id=session_id)
            return {}
    
    # 同步版本的方法，用于在异步上下文中需要同步日志记录的场景
    def log_error_sync(self, error_type: str, error_message: str, context: Optional[Dict] = None):
        """同步记录错误（用于异步上下文中需要同步日志记录的情况）"""
        try:
            timestamp = datetime.now()
            
            log_data = {
                "timestamp": timestamp.isoformat(),
                "error_type": error_type,
                "error_message": error_message,
                "context": context or {}
            }
            
            self.system_logger.error("system_error", **log_data)
            
        except Exception as e:
            print(f"同步记录错误日志失败: {e}")
    
    def log_system_event_sync(self, event_type: str, message: str, details: Optional[Dict] = None):
        """同步记录系统事件"""
        try:
            timestamp = datetime.now()
            
            log_data = {
                "timestamp": timestamp.isoformat(),
                "event_type": event_type,
                "message": message,
                "details": details or {}
            }
            
            self.system_logger.info("system_event", **log_data)
            
        except Exception as e:
            print(f"同步记录系统事件失败: {e}")
    
    def log_performance_sync(self, operation: str, duration: float, details: Optional[Dict] = None):
        """同步记录性能信息"""
        try:
            timestamp = datetime.now()
            
            log_data = {
                "timestamp": timestamp.isoformat(),
                "operation": operation,
                "duration": duration,
                "duration_ms": duration * 1000,
                "details": details or {}
            }
            
            # 根据性能表现设置不同级别
            if duration > 5.0:  # 超过5秒的慢操作
                self.performance_logger.warning("slow_operation", **log_data)
            else:
                self.performance_logger.info("performance_metric", **log_data)
            
        except Exception as e:
            print(f"同步记录性能日志失败: {e}")

# 全局日志管理器实例
logger_manager = LoggerManager()