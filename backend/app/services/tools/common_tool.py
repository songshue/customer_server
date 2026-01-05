#!/usr/bin/env python3
"""
通用工具 - 提供通用的工具函数
"""
import os
import sys
import re
import json
import hashlib
import uuid
import time
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
import logging

# 确保当前目录在Python路径中
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CommonTool:
    """通用工具类"""
    
    def __init__(self):
        """初始化通用工具"""
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def validate_order_id(self, order_id: str) -> bool:
        """验证订单ID格式"""
        if not order_id:
            return False
        
        # 简单的订单ID验证：包含字母数字，长度6-20
        pattern = r'^[A-Za-z0-9]{6,20}$'
        return bool(re.match(pattern, order_id))
    
    def validate_phone_number(self, phone: str) -> bool:
        """验证手机号格式"""
        if not phone:
            return False
        
        # 验证中国手机号格式
        pattern = r'^1[3-9]\d{9}$'
        return bool(re.match(pattern, phone.replace('*', '').replace('-', '')))
    
    def extract_order_id_from_text(self, text: str) -> Optional[str]:
        """从文本中提取订单号"""
        if not text:
            return None
        
        # 寻找订单号模式
        patterns = [
            r'订单号[：:\s]*([A-Za-z0-9]{6,20})',
            r'订单[：:\s]*([A-Za-z0-9]{6,20})',
            r'Order[：:\s]*([A-Za-z0-9]{6,20})',
            r'NO[：:\s]*([A-Za-z0-9]{6,20})',
            r'([A-Za-z0-9]{6,20})'  # 通用匹配
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                order_id = match.group(1)
                if self.validate_order_id(order_id):
                    return order_id
        
        return None
    
    def extract_phone_from_text(self, text: str) -> Optional[str]:
        """从文本中提取手机号"""
        if not text:
            return None
        
        # 寻找手机号模式
        patterns = [
            r'手机[号号]?[：:\s]*(\d{3}\*{4}\d{4})',
            r'手机[号号]?[：:\s]*(\d{11})',
            r'联系电话[：:\s]*(\d{3}\*{4}\d{4})',
            r'联系电话[：:\s]*(\d{11})',
            r'电话[：:\s]*(\d{3}\*{4}\d{4})',
            r'电话[：:\s]*(\d{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                phone = match.group(1)
                if self.validate_phone_number(phone):
                    return phone
        
        return None
    
    def mask_phone_number(self, phone: str) -> str:
        """脱敏手机号"""
        if not phone or len(phone) != 11:
            return phone
        
        return phone[:3] + '****' + phone[-4:]
    
    def generate_session_id(self) -> str:
        """生成会话ID"""
        return str(uuid.uuid4())
    
    def generate_uuid(self) -> str:
        """生成UUID"""
        return str(uuid.uuid4())
    
    def format_datetime(self, dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """格式化时间"""
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            except:
                return dt
        
        return dt.strftime(format_str)
    
    def calculate_time_difference(self, start_time: datetime, end_time: datetime = None) -> float:
        """计算时间差（秒）"""
        if end_time is None:
            end_time = datetime.now()
        
        if isinstance(start_time, str):
            try:
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except:
                start_time = datetime.now()
        
        if isinstance(end_time, str):
            try:
                end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except:
                end_time = datetime.now()
        
        return (end_time - start_time).total_seconds()
    
    def is_business_hours(self) -> bool:
        """检查是否在工作时间（9:00-18:00）"""
        now = datetime.now()
        current_hour = now.hour
        
        # 周一到周五，9:00-18:00
        return 0 <= now.weekday() <= 4 and 9 <= current_hour < 18
    
    def format_price(self, price: Union[float, int], currency: str = "¥") -> str:
        """格式化价格"""
        if isinstance(price, str):
            try:
                price = float(price)
            except:
                return price
        
        return f"{currency}{price:,.2f}"
    
    def truncate_text(self, text: str, max_length: int = 100, suffix: str = "...") -> str:
        """截断文本"""
        if not text or len(text) <= max_length:
            return text
        
        return text[:max_length - len(suffix)] + suffix
    
    def clean_text(self, text: str) -> str:
        """清理文本"""
        if not text:
            return ""
        
        # 去除多余空格和换行
        text = re.sub(r'\s+', ' ', text.strip())
        
        # 去除特殊字符
        text = re.sub(r'[^\w\s\-.,!?！？。：]', '', text)
        
        return text
    
    def extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        """提取关键词"""
        if not text:
            return []
        
        # 简单的关键词提取：去除停用词，获取频率最高的词
        stop_words = {'的', '了', '在', '是', '我', '你', '他', '她', '它', '们', '这', '那', '有', '没有', '不', '要', '不'}
        
        # 分词（简单实现）
        words = re.findall(r'\w+', text)
        
        # 过滤停用词和短词
        keywords = [word for word in words if len(word) > 1 and word not in stop_words]
        
        # 统计频率
        word_freq = {}
        for word in keywords:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # 按频率排序
        sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        
        return [word for word, freq in sorted_keywords[:max_keywords]]
    
    def validate_email(self, email: str) -> bool:
        """验证邮箱格式"""
        if not email:
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def hash_string(self, text: str, algorithm: str = 'md5') -> str:
        """计算字符串哈希值"""
        try:
            if algorithm.lower() == 'md5':
                return hashlib.md5(text.encode('utf-8')).hexdigest()
            elif algorithm.lower() == 'sha256':
                return hashlib.sha256(text.encode('utf-8')).hexdigest()
            else:
                raise ValueError(f"不支持的哈希算法: {algorithm}")
        except Exception as e:
            self.logger.error(f"计算哈希失败: {e}")
            return ""
    
    def safe_json_loads(self, json_str: str, default: Any = None) -> Any:
        """安全的JSON解析"""
        try:
            return json.loads(json_str)
        except (json.JSONDecodeError, TypeError) as e:
            self.logger.debug(f"JSON解析失败: {e}")
            return default
    
    def safe_json_dumps(self, obj: Any, default: Any = None) -> str:
        """安全的JSON序列化"""
        try:
            return json.dumps(obj, ensure_ascii=False, default=default or str)
        except (TypeError, ValueError) as e:
            self.logger.debug(f"JSON序列化失败: {e}")
            return "{}"
    
    def retry_on_failure(self, max_retries: int = 3, delay: float = 1.0):
        """重试装饰器"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                for attempt in range(max_retries + 1):
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        if attempt == max_retries:
                            self.logger.error(f"函数 {func.__name__} 在{max_retries}次重试后仍然失败: {e}")
                            raise e
                        
                        self.logger.warning(f"函数 {func.__name__} 第{attempt + 1}次尝试失败: {e}")
                        await asyncio.sleep(delay * (2 ** attempt))  # 指数退避
                
            return wrapper
        return decorator