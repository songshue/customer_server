"""
任务调度器
负责执行定期任务，如清理旧消息等
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable

logger = logging.getLogger(__name__)

class TaskScheduler:
    """任务调度器"""
    
    def __init__(self):
        self.tasks = []
        self.running = False
        
    def schedule_task(self, task_func: Callable, interval_seconds: int, *args, **kwargs):
        """
        调度定期任务
        
        Args:
            task_func: 要执行的任务函数
            interval_seconds: 任务执行间隔（秒）
            *args, **kwargs: 传递给任务函数的参数
        """
        self.tasks.append({
            "func": task_func,
            "interval": interval_seconds,
            "args": args,
            "kwargs": kwargs,
            "last_run": None
        })
        logger.info(f"已调度任务 {task_func.__name__}，间隔: {interval_seconds} 秒")
    
    async def start(self):
        """启动任务调度器"""
        if self.running:
            return
        
        self.running = True
        logger.info("任务调度器启动")
        
        # 为每个任务创建协程
        for task_info in self.tasks:
            asyncio.create_task(self._run_task(task_info))
    
    async def stop(self):
        """停止任务调度器"""
        self.running = False
        logger.info("任务调度器停止")
    
    async def _run_task(self, task_info: dict):
        """运行单个定期任务"""
        while self.running:
            try:
                # 计算下一次运行时间
                interval = task_info["interval"]
                last_run = task_info["last_run"]
                now = datetime.now()
                
                # 如果任务从未运行过，或者已经超过间隔时间，则运行任务
                if not last_run or (now - last_run).total_seconds() >= interval:
                    logger.info(f"执行任务 {task_info['func'].__name__}...")
                    await task_info["func"](*task_info["args"], **task_info["kwargs"])
                    task_info["last_run"] = now
                    logger.info(f"任务 {task_info['func'].__name__} 执行完成")
                else:
                    # 计算下次运行的剩余时间
                    next_run = last_run + timedelta(seconds=interval)
                    remaining = (next_run - now).total_seconds()
                    logger.debug(f"任务 {task_info['func'].__name__} 将在 {remaining:.1f} 秒后运行")
                
                # 等待指定间隔时间
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"任务执行失败: {e}")
                # 任务失败后，等待一个间隔再重试
                await asyncio.sleep(task_info["interval"])

# 创建全局调度器实例
task_scheduler = TaskScheduler()