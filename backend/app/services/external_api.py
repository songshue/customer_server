#!/usr/bin/env python3
"""
物流API模拟服务
功能：提供模拟物流状态查询、快递追踪、配送信息等
"""
import os
import sys
import json
import random
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LogisticsStatus(str, Enum):
    """物流状态枚举"""
    PENDING = "pending"
    PICKED_UP = "picked_up"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    EXCEPTION = "exception"
    RETURNED = "returned"

class ShippingCarrier(str, Enum):
    """快递公司枚举"""
    SF_EXPRESS = "顺丰速运"
    YTO_EXPRESS = "圆通速递"
    ZTO_EXPRESS = "中通快递"
    STO_EXPRESS = "申通快递"
    JD_LOGISTICS = "京东物流"
    YUNDA_EXPRESS = "韵达快递"

@dataclass
class TrackingEvent:
    """物流追踪事件"""
    timestamp: str
    status: str
    location: str
    description: str

@dataclass
class LogisticsInfo:
    """物流信息"""
    tracking_number: str
    carrier: str
    status: str
    origin: str
    destination: str
    estimated_delivery: str
    events: List[TrackingEvent] = field(default_factory=list)
    sender: str = ""
    receiver: str = ""
    weight: float = 0.0
    cost: float = 0.0

class MockLogisticsDatabase:
    """模拟物流数据库"""
    
    def __init__(self):
        self.logistics_data: Dict[str, LogisticsInfo] = {}
        self._init_mock_data()
    
    def _init_mock_data(self):
        """初始化模拟数据"""
        carriers = list(ShippingCarrier)
        
        mock_tracking_numbers = [
            f"SF{random.randint(1000000000, 9999999999)}",
            f"YT{random.randint(1000000000, 9999999999)}",
            f"ZT{random.randint(1000000000, 9999999999)}",
            f"JD{random.randint(1000000000, 9999999999)}"
        ]
        
        for tracking_num in mock_tracking_numbers:
            carrier = random.choice(carriers)
            status = random.choice(list(LogisticsStatus))
            self.logistics_data[tracking_num] = self._generate_mock_logistics(tracking_num, carrier.value, status)
    
    def _generate_mock_logistics(
        self, 
        tracking_number: str, 
        carrier: str, 
        status: LogisticsStatus
    ) -> LogisticsInfo:
        """生成模拟物流信息"""
        
        cities = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "西安", "南京", "重庆"]
        origins = random.sample(cities, 2)
        destinations = [c for c in cities if c not in origins][:1]
        
        events = self._generate_tracking_events(status, origins[0], destinations[0] if destinations else origins[0])
        
        estimated_days = random.randint(1, 5)
        estimated_delivery = (datetime.now() + timedelta(days=estimated_days)).strftime("%Y-%m-%d %H:%M:%S")
        
        return LogisticsInfo(
            tracking_number=tracking_number,
            carrier=carrier,
            status=status.value,
            origin=origins[0],
            destination=destinations[0] if destinations else "未知",
            estimated_delivery=estimated_delivery,
            events=events,
            sender="张三",
            receiver="李四",
            weight=round(random.uniform(0.5, 10.0), 2),
            cost=round(random.uniform(10, 100), 2)
        )
    
    def _generate_tracking_events(
        self, 
        status: LogisticsStatus, 
        origin: str, 
        destination: str
    ) -> List[TrackingEvent]:
        """生成物流追踪事件"""
        events = []
        base_time = datetime.now()
        
        event_configs = {
            LogisticsStatus.PENDING: [
                ("order_received", "订单已创建", origin)
            ],
            LogisticsStatus.PICKED_UP: [
                ("order_received", "订单已创建", origin),
                ("picked_up", "快递员已揽收", origin)
            ],
            LogisticsStatus.IN_TRANSIT: [
                ("order_received", "订单已创建", origin),
                ("picked_up", "快递员已揽收", origin),
                ("transit_1", "运输中", origin),
                ("transit_2", "运输中", random.choice(["武汉", "郑州", "南京"]))
            ],
            LogisticsStatus.OUT_FOR_DELIVERY: [
                ("order_received", "订单已创建", origin),
                ("picked_up", "快递员已揽收", origin),
                ("transit_1", "运输中", origin),
                ("arrived_hub", "到达配送站点", destination),
                ("out_for_delivery", "派送中", destination)
            ],
            LogisticsStatus.DELIVERED: [
                ("order_received", "订单已创建", origin),
                ("picked_up", "快递员已揽收", origin),
                ("transit_1", "运输中", origin),
                ("arrived_hub", "到达配送站点", destination),
                ("out_for_delivery", "派送中", destination),
                ("delivered", "已签收", destination)
            ],
            LogisticsStatus.EXCEPTION: [
                ("order_received", "订单已创建", origin),
                ("picked_up", "快递员已揽收", origin),
                ("exception", "配送异常", random.choice(cities))
            ],
            LogisticsStatus.RETURNED: [
                ("order_received", "订单已创建", origin),
                ("picked_up", "快递员已揽收", origin),
                ("transit_1", "运输中", origin),
                ("returned", "已退回", origin)
            ]
        }
        
        selected_events = event_configs.get(status, event_configs[LogisticsStatus.IN_TRANSIT])
        
        for i, (event_type, description, location) in enumerate(selected_events):
            event_time = base_time - timedelta(hours=(len(selected_events) - i) * 6)
            events.append(TrackingEvent(
                timestamp=event_time.strftime("%Y-%m-%d %H:%M:%S"),
                status=event_type,
                location=location,
                description=description
            ))
        
        return events
    
    def get_logistics(self, tracking_number: str) -> Optional[LogisticsInfo]:
        """获取物流信息"""
        return self.logistics_data.get(tracking_number)
    
    def create_logistics(self, logistics_info: LogisticsInfo) -> LogisticsInfo:
        """创建物流信息"""
        self.logistics_data[logistics_info.tracking_number] = logistics_info
        return logistics_info
    
    def update_status(self, tracking_number: str, status: LogisticsStatus) -> bool:
        """更新物流状态"""
        if tracking_number in self.logistics_data:
            self.logistics_data[tracking_number].status = status.value
            return True
        return False

class LogisticsAPIService:
    """物流API服务类"""
    
    def __init__(self):
        self.db = MockLogisticsDatabase()
        self._init_sample_data()
    
    def _init_sample_data(self):
        """初始化示例数据"""
        sample_tracking_numbers = [
            "SF1234567890",
            "YT0987654321",
            "ZT1122334455"
        ]
        
        for i, tracking_num in enumerate(sample_tracking_numbers):
            if tracking_num not in self.db.logistics_data:
                carrier = list(ShippingCarrier)[i % len(ShippingCarrier)]
                status = list(LogisticsStatus)[min(i, len(LogisticsStatus) - 1)]
                self.db.create_logistics(
                    self.db._generate_mock_logistics(tracking_num, carrier.value, status)
                )
    
    async def get_tracking_info(self, tracking_number: str) -> Dict[str, Any]:
        """
        获取物流追踪信息
        
        Args:
            tracking_number: 快递单号
            
        Returns:
            物流信息字典
        """
        await asyncio.sleep(0.1)
        
        logistics_info = self.db.get_logistics(tracking_number)
        
        if not logistics_info:
            return {
                "success": False,
                "message": f"未找到物流单号: {tracking_number}",
                "tracking_number": tracking_number
            }
        
        return {
            "success": True,
            "data": {
                "tracking_number": logistics_info.tracking_number,
                "carrier": logistics_info.carrier,
                "status": logistics_info.status,
                "status_display": self._get_status_display(logistics_info.status),
                "origin": logistics_info.origin,
                "destination": logistics_info.destination,
                "estimated_delivery": logistics_info.estimated_delivery,
                "sender": logistics_info.sender,
                "receiver": logistics_info.receiver,
                "weight": logistics_info.weight,
                "cost": logistics_info.cost,
                "events": [
                    {
                        "timestamp": event.timestamp,
                        "status": event.status,
                        "location": event.location,
                        "description": event.description
                    }
                    for event in logistics_info.events
                ]
            }
        }
    
    def _get_status_display(self, status: str) -> str:
        """获取状态的中文显示"""
        status_map = {
            "pending": "待揽收",
            "picked_up": "已揽收",
            "in_transit": "运输中",
            "out_for_delivery": "派送中",
            "delivered": "已签收",
            "exception": "配送异常",
            "returned": "已退回"
        }
        return status_map.get(status, status)
    
    async def get_delivery_status(self, tracking_number: str) -> Dict[str, Any]:
        """
        获取配送状态（简化版）
        
        Args:
            tracking_number: 快递单号
            
        Returns:
            配送状态信息
        """
        result = await self.get_tracking_info(tracking_number)
        
        if not result.get("success"):
            return result
        
        data = result["data"]
        return {
            "success": True,
            "tracking_number": tracking_number,
            "carrier": data["carrier"],
            "status": data["status"],
            "status_display": data["status_display"],
            "destination": data["destination"],
            "estimated_delivery": data["estimated_delivery"]
        }
    
    async def estimate_delivery_time(self, origin: str, destination: str) -> Dict[str, Any]:
        """
        估算配送时间
        
        Args:
            origin: 发货地
            destination: 目的地
            
        Returns:
            配送时间估算
        """
        await asyncio.sleep(0.05)
        
        cities = ["北京", "上海", "广州", "深圳", "杭州"]
        if origin in cities and destination in cities:
            days = random.randint(1, 3)
        else:
            days = random.randint(2, 5)
        
        return {
            "success": True,
            "origin": origin,
            "destination": destination,
            "estimated_days": days,
            "estimated_date": (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        }
    
    async def get_carrier_info(self, carrier_code: str) -> Dict[str, Any]:
        """
        获取快递公司信息
        
        Args:
            carrier_code: 快递公司代码
            
        Returns:
            快递公司信息
        """
        await asyncio.sleep(0.05)
        
        carrier_map = {
            "SF": {"name": "顺丰速运", "code": "SF", "hotline": "95338"},
            "YT": {"name": "圆通速递", "code": "YT", "hotline": "95554"},
            "ZT": {"name": "中通快递", "code": "ZT", "hotline": "95311"},
            "STO": {"name": "申通快递", "code": "STO", "hotline": "95543"},
            "JD": {"name": "京东物流", "code": "JD", "hotline": "950616"},
            "YD": {"name": "韵达快递", "code": "YD", "hotline": "95546"}
        }
        
        carrier = carrier_map.get(carrier_code.upper())
        if carrier:
            return {
                "success": True,
                "data": carrier
            }
        
        return {
            "success": False,
            "message": f"未找到快递公司: {carrier_code}"
        }

logistics_service = LogisticsAPIService()

async def get_logistics_status(tracking_number: str) -> str:
    """
    获取物流状态的工具函数（用于LangChain Tool）
    
    Args:
        tracking_number: 快递单号
        
        Returns:
        格式化的物流状态信息
    """
    result = await logistics_service.get_delivery_status(tracking_number)
    
    if not result.get("success"):
        return f"未找到物流单号 {tracking_number} 的信息"
    
    return (
        f"物流单号: {tracking_number}\n"
        f"快递公司: {result['carrier']}\n"
        f"配送状态: {result['status_display']}\n"
        f"目的地: {result['destination']}\n"
        f"预计送达: {result['estimated_delivery']}"
    )

async def track_package(tracking_number: str) -> str:
    """
    追踪包裹的详细物流信息（用于LangChain Tool）
    
    Args:
        tracking_number: 快递单号
        
        Returns:
        格式化的追踪信息
    """
    result = await logistics_service.get_tracking_info(tracking_number)
    
    if not result.get("success"):
        return f"未找到物流单号 {tracking_number} 的信息"
    
    data = result["data"]
    lines = [
        f"快递单号: {tracking_number}",
        f"快递公司: {data['carrier']}",
        f"当前状态: {data['status_display']}",
        f"发货地: {data['origin']}",
        f"收货地: {data['destination']}",
        f"预计送达: {data['estimated_delivery']}",
        "",
        "物流轨迹:"
    ]
    
    for event in data["events"]:
        lines.append(f"  {event['timestamp']} | {event['location']} | {event['description']}")
    
    return "\n".join(lines)

def get_logistics_service() -> LogisticsAPIService:
    """获取物流API服务实例"""
    return logistics_service
