#!/usr/bin/env python3
"""
日志工具 - 提供日志记录相关的工具函数
"""
import os
import sys
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json

# 确保当前目录在Python路径中
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LoggerTool:
    """日志工具类"""
    
    def __init__(self, logger_instance: logging.Logger = None):
        """初始化日志工具"""
        self.logger = logger_instance or logger
        self.log_level = logging.INFO
        
    async def log_system_event(self, event_type: str, message: str, 
                              details: Dict[str, Any] = None) -> None:
        """记录系统事件"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type,
                "message": message,
                "details": details or {}
            }
            
            self.logger.info(f"系统事件 [{event_type}]: {message}")
            if details:
                self.logger.debug(f"事件详情: {json.dumps(details, ensure_ascii=False, indent=2)}")
                
        except Exception as e:
            self.logger.error(f"记录系统事件失败: {e}")
    
    async def log_user_interaction(self, user_id: str, session_id: str, 
                                  user_input: str, agent_response: str,
                                  metadata: Dict[str, Any] = None) -> None:
        """记录用户交互"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "session_id": session_id,
                "user_input": user_input,
                "agent_response": agent_response,
                "metadata": metadata or {}
            }
            
            self.logger.info(f"用户交互 [{user_id}]: {user_input[:50]}...")
            self.logger.debug(f"交互详情: {json.dumps(log_entry, ensure_ascii=False, indent=2)}")
            
        except Exception as e:
            self.logger.error(f"记录用户交互失败: {e}")
    
    async def log_agent_action(self, agent_name: str, action: str, 
                              input_data: str, output_data: str,
                              success: bool = True, error_message: str = None) -> None:
        """记录Agent操作"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "agent_name": agent_name,
                "action": action,
                "input_data": input_data[:200] + "..." if len(input_data) > 200 else input_data,
                "output_data": output_data[:200] + "..." if len(output_data) > 200 else output_data,
                "success": success,
                "error_message": error_message
            }
            
            status = "成功" if success else "失败"
            self.logger.info(f"Agent操作 [{agent_name} - {action}]: {status}")
            
            if not success and error_message:
                self.logger.error(f"Agent错误: {error_message}")
                
        except Exception as e:
            self.logger.error(f"记录Agent操作失败: {e}")
    
    async def log_performance_metrics(self, operation: str, duration: float,
                                     metadata: Dict[str, Any] = None) -> None:
        """记录性能指标"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "operation": operation,
                "duration_seconds": duration,
                "metadata": metadata or {}
            }
            
            self.logger.info(f"性能指标 [{operation}]: {duration:.3f}s")
            
            # 性能警告
            if duration > 5.0:
                self.logger.warning(f"性能警告: {operation} 耗时 {duration:.3f}s")
                
        except Exception as e:
            self.logger.error(f"记录性能指标失败: {e}")
    
    async def log_error(self, error_type: str, error_message: str, 
                       context: Dict[str, Any] = None) -> None:
        """记录错误信息"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "error_type": error_type,
                "error_message": error_message,
                "context": context or {}
            }
            
            self.logger.error(f"错误 [{error_type}]: {error_message}")
            if context:
                self.logger.debug(f"错误上下文: {json.dumps(context, ensure_ascii=False, indent=2)}")
                
        except Exception as e:
            self.logger.error(f"记录错误失败: {e}")
    
    def set_log_level(self, level: str) -> None:
        """设置日志级别"""
        try:
            level_map = {
                "DEBUG": logging.DEBUG,
                "INFO": logging.INFO,
                "WARNING": logging.WARNING,
                "ERROR": logging.ERROR,
                "CRITICAL": logging.CRITICAL
            }
            
            if level.upper() in level_map:
                self.log_level = level_map[level.upper()]
                self.logger.setLevel(self.log_level)
                
        except Exception as e:
            self.logger.error(f"设置日志级别失败: {e}")
    
    async def debug(self, message: str, details: Dict[str, Any] = None) -> None:
        """调试日志"""
        try:
            if details:
                self.logger.debug(f"{message}: {json.dumps(details, ensure_ascii=False, indent=2)}")
            else:
                self.logger.debug(message)
                
        except Exception as e:
            self.logger.error(f"记录调试日志失败: {e}")
    
    async def info(self, message: str, details: Dict[str, Any] = None) -> None:
        """信息日志"""
        try:
            if details:
                self.logger.info(f"{message}: {json.dumps(details, ensure_ascii=False, indent=2)}")
            else:
                self.logger.info(message)
                
        except Exception as e:
            self.logger.error(f"记录信息日志失败: {e}")
    
    async def warning(self, message: str, details: Dict[str, Any] = None) -> None:
        """警告日志"""
        try:
            if details:
                self.logger.warning(f"{message}: {json.dumps(details, ensure_ascii=False, indent=2)}")
            else:
                self.logger.warning(message)
                
        except Exception as e:
            self.logger.error(f"记录警告日志失败: {e}")
    
    async def error(self, message: str, details: Dict[str, Any] = None) -> None:
        """错误日志"""
        try:
            if details:
                self.logger.error(f"{message}: {json.dumps(details, ensure_ascii=False, indent=2)}")
            else:
                self.logger.error(message)
                
        except Exception as e:
            self.logger.error(f"记录错误日志失败: {e}")