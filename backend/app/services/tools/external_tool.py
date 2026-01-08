#!/usr/bin/env python3
"""
外部API工具模块
功能：将外部API封装为LangChain Tool
"""
import os
import sys
import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from langchain_core.tools import tool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.external_api import (
    get_logistics_service,
    get_logistics_status as get_logistics_status_api,
    track_package as track_package_api
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LogisticsTools:
    """物流相关工具类"""
    
    def __init__(self):
        self.service = get_logistics_service()
    
    async def get_logistics_status(self, tracking_number: str) -> str:
        """
        获取物流配送状态
        
        Args:
            tracking_number: 快递单号
            
        Returns:
            物流状态信息
        """
        return await get_logistics_status_api(tracking_number)
    
    async def track_package(self, tracking_number: str) -> str:
        """
        追踪包裹物流轨迹
        
        Args:
            tracking_number: 快递单号
            
        Returns:
            详细物流轨迹
        """
        return await track_package_api(tracking_number)
    
    async def estimate_delivery(self, origin: str, destination: str) -> str:
        """
        估算配送时间
        
        Args:
            origin: 发货地
            destination: 目的地
            
        Returns:
            配送时间估算
        """
        result = await self.service.estimate_delivery_time(origin, destination)
        
        if result.get("success"):
            return (
                f"从 {origin} 到 {destination}\n"
                f"预计配送天数: {result['estimated_days']} 天\n"
                f"预计送达日期: {result['estimated_date']}"
            )
        else:
            return f"无法估算配送时间: {result.get('message')}"

logistics_tools = LogisticsTools()

@tool
async def get_logistics_status_tool(tracking_number: str) -> str:
    """
    获取快递物流配送状态。
    
    Args:
        tracking_number: 快递单号，例如 SF1234567890, YT0987654321
        
    Returns:
        格式化的物流状态信息，包含当前状态、快递公司、目的地等
    """
    """获取物流配送状态"""
    return await logistics_tools.get_logistics_status(tracking_number)

@tool
async def track_package_tool(tracking_number: str) -> str:
    """
    追踪快递包裹的完整物流轨迹。
    
    Args:
        tracking_number: 快递单号，例如 SF1234567890, YT0987654321
        
    Returns:
        详细的物流轨迹信息，包含所有历史节点
    """
    """追踪包裹"""
    return await logistics_tools.track_package(tracking_number)

@tool
async def estimate_delivery_tool(origin: str, destination: str) -> str:
    """
    估算两个城市之间的快递配送时间。
    
    Args:
        origin: 发货城市，例如 北京、上海、广州
        destination: 收货城市，例如 深圳、杭州、成都
        
    Returns:
        配送时间估算信息
    """
    """估算配送时间"""
    return await logistics_tools.estimate_delivery(origin, destination)

def get_logistics_tools() -> List:
    """获取所有物流相关工具"""
    return [
        get_logistics_status_tool,
        track_package_tool,
        estimate_delivery_tool
    ]
