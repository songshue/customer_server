#!/usr/bin/env python3
"""
数据库工具 - 提供数据库操作相关的工具函数
"""
import os
import sys
import logging
from typing import Dict, Any, List, Optional
import json

# 确保当前目录在Python路径中
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 导入数据库管理器
try:
    from ...managers.mysql_manager import mysql_manager
except ImportError as e:
    logging.warning(f"导入mysql_manager失败: {e}")
    mysql_manager = None

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseTool:
    """数据库工具类"""
    
    def __init__(self, db_manager=None):
        """初始化数据库工具"""
        self.db_manager = db_manager or mysql_manager
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def query_order_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """根据订单ID查询订单信息"""
        try:
            if not self.db_manager:
                # 模拟订单数据
                return {
                    "order_id": order_id,
                    "status": "已发货",
                    "product_name": "iPhone 15 Pro",
                    "price": 8999.00,
                    "order_date": "2024-01-15",
                    "delivery_date": "2024-01-18",
                    "address": "北京市朝阳区xxx街道xxx号",
                    "customer_name": "张三",
                    "customer_phone": "138****5678",
                    "quantity": 1,
                    "payment_status": "已支付"
                }
            
            # 实际数据库查询 - 修正字段名以匹配orders表结构
            query = """
            SELECT order_id, order_status, product_name, total_amount, created_at, 
                   delivered_at, user_address, user_name, user_phone,
                   quantity, payment_status
            FROM orders 
            WHERE order_id = %s
            """
            
            result = await self.db_manager.execute_query(query, (order_id,))
            
            if result:
                row = result[0]  # row 是字典
                return {
                    "order_id": row["order_id"],
                    "status": row["order_status"],
                    "product_name": row["product_name"],
                    "price": float(row["total_amount"]),
                    "order_date": row["created_at"].isoformat() if hasattr(row["created_at"], 'isoformat') else str(row["created_at"]),
                    "delivery_date": row["delivered_at"].isoformat() if hasattr(row["delivered_at"], 'isoformat') else str(row["delivered_at"]) if row["delivered_at"] else None,
                    "address": row["user_address"],
                    "customer_name": row["user_name"],
                    "customer_phone": row["user_phone"],
                    "quantity": row["quantity"],
                    "payment_status": row["payment_status"]
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"查询订单失败: {e}")
            return None
    
    async def query_products(self, category: str = None, keyword: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """查询产品信息"""
        try:
            if not self.db_manager:
                # 模拟产品数据
                mock_products = [
                    {
                        "product_id": "P001",
                        "name": "iPhone 15 Pro",
                        "category": "手机",
                        "price": 8999.00,
                        "specs": "256GB, 钛金色",
                        "description": "最新款iPhone，搭载A17芯片"
                    },
                    {
                        "product_id": "P002", 
                        "name": "MacBook Pro",
                        "category": "笔记本",
                        "price": 15999.00,
                        "specs": "16英寸, M3芯片",
                        "description": "专业级笔记本电脑"
                    }
                ]
                
                if category:
                    mock_products = [p for p in mock_products if p["category"] == category]
                if keyword:
                    mock_products = [p for p in mock_products if keyword in p["name"] or keyword in p["description"]]
                
                return mock_products[:limit]
            
            # 实际数据库查询
            query = """
            SELECT product_id, name, category, price, specs, description
            FROM products
            WHERE 1=1
            """
            params = []
            
            if category:
                query += " AND category = %s"
                params.append(category)
            
            if keyword:
                query += " AND (name LIKE %s OR description LIKE %s)"
                params.extend([f"%{keyword}%", f"%{keyword}%"])
            
            query += " LIMIT %s"
            params.append(limit)
            
            result = await self.db_manager.execute_query(query, params)
            
            if result:
                return [
                    {
                        "product_id": row[0],
                        "name": row[1],
                        "category": row[2],
                        "price": float(row[3]),
                        "specs": row[4],
                        "description": row[5]
                    }
                    for row in result
                ]
            
            return []
            
        except Exception as e:
            self.logger.error(f"查询产品失败: {e}")
            return []
    
    async def save_ai_response(self, user_id: str, session_id: str, user_message: str, 
                             ai_message: str, metadata: Dict[str, Any] = None) -> bool:
        """保存AI回复到数据库"""
        try:
            if not self.db_manager:
                self.logger.info("数据库管理器不可用，跳过保存AI回复")
                return True
            
            # 保存用户消息 - created_at字段有默认值CURRENT_TIMESTAMP，不需要显式传入
            user_query = """
            INSERT INTO chat_messages (user_id, session_id, message_type, content, 
                                     message_metadata) 
            VALUES (%s, %s, %s, %s, %s)
            """
            
            # 保存AI回复 - created_at字段有默认值CURRENT_TIMESTAMP，不需要显式传入
            ai_query = """
            INSERT INTO chat_messages (user_id, session_id, message_type, content, 
                                     message_metadata) 
            VALUES (%s, %s, %s, %s, %s)
            """
            
            metadata_json = json.dumps(metadata or {}, ensure_ascii=False)
            
            # 先保存用户消息
            await self.db_manager.execute_query(
                user_query, 
                (user_id, session_id, 'user', user_message, metadata_json)
            )
            
            # 再保存AI回复
            await self.db_manager.execute_query(
                ai_query, 
                (user_id, session_id, 'assistant', ai_message, metadata_json)
            )
            
            self.logger.info(f"AI回复已保存: 用户{user_id}, 会话{session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存AI回复失败: {e}")
            return False
    
    async def get_user_orders(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """获取用户订单列表"""
        try:
            if not self.db_manager:
                # 模拟用户订单数据
                return [
                    {
                        "order_id": "ORD001",
                        "status": "已发货",
                        "product_name": "iPhone 15 Pro",
                        "price": 8999.00,
                        "order_date": "2024-01-15",
                        "delivery_date": "2024-01-18"
                    },
                    {
                        "order_id": "ORD002",
                        "status": "已送达",
                        "product_name": "AirPods Pro",
                        "price": 1999.00,
                        "order_date": "2024-01-10",
                        "delivery_date": "2024-01-12"
                    }
                ][:limit]
            
            # 实际数据库查询
            query = """
            SELECT order_id, status, product_name, price, order_date, delivery_date
            FROM orders 
            WHERE customer_id = %s
            ORDER BY order_date DESC
            LIMIT %s
            """
            
            result = await self.db_manager.execute_query(query, (user_id, limit))
            
            if result:
                return [
                    {
                        "order_id": row[0],
                        "status": row[1],
                        "product_name": row[2],
                        "price": float(row[3]),
                        "order_date": row[4].isoformat() if hasattr(row[4], 'isoformat') else str(row[4]),
                        "delivery_date": row[5].isoformat() if hasattr(row[5], 'isoformat') else str(row[5])
                    }
                    for row in result
                ]
            
            return []
            
        except Exception as e:
            self.logger.error(f"获取用户订单失败: {e}")
            return []