"""
反馈分析器
负责定期分析用户反馈，统计低评分对话，并发送邮件通知
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.managers.mysql_manager import mysql_manager
from app.managers.logger_manager import logger_manager

logger = logging.getLogger(__name__)

class FeedbackAnalyzer:
    """反馈分析器"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.mail_service = None  # 可以替换为实际的邮件服务
    
    async def analyze_low_rating_feedbacks(self):
        """
        分析低评分反馈（评分 < 3）
        """
        try:
            # 获取最近7天的低评分反馈
            low_rating_feedbacks = await mysql_manager.get_low_rating_feedbacks(days=7)
            
            if not low_rating_feedbacks:
                logger.info("最近7天没有低评分反馈")
                return
            
            logger.info(f"找到 {len(low_rating_feedbacks)} 条低评分反馈")
            
            # 提取关键词（简单实现，实际可以使用NLP库）
            keywords = self._extract_keywords(low_rating_feedbacks)
            
            # 生成统计报告
            report = self._generate_report(low_rating_feedbacks, keywords)
            
            # 发送邮件通知运营
            await self._send_report_email(report)
            
        except Exception as e:
            logger.error(f"分析低评分反馈失败: {e}")
            await logger_manager.log_error('feedback_analysis_error', str(e), trace_id=str(hash(datetime.now())))
    
    def _extract_keywords(self, feedbacks: List[Dict]) -> List[str]:
        """
        从反馈中提取关键词
        
        Args:
            feedbacks: 反馈列表
            
        Returns:
            关键词列表
        """
        # 简单实现：统计常见词
        word_count = {}
        stop_words = {
            '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要',
            '去', '你', '会', '着', '没有', '看', '好', '自己', '这', '来', '他们', '对', '小', '中', '大', '为',
            '现在', '可以', '那', '我们', '时', '想', '能', '出', '而', '以', '后', '再', '更', '得', '应',
            '由', '与', '比', '向', '往', '里', '前', '但', '然而', '却', '又', '还', '才', '并',
            '且', '或', '以及', '但是', '可是', '不过', '因为', '所以', '因此', '于是', '结果',
            '此外', '同时', '例如', '比如', '另外', '虽然', '既然', '如果', '假如', '倘若', '要是', '即使', '尽管',
            '不管', '无论', '只有', '只要', '除非', '以免', '以便', '之所以', '是因为', '首先', '其次', '再次',
            '最后', '第一', '第二', '第三', '总之', '综上所述', '由此可见', '因而', '从而',
            '然后', '后来', '接着', '最终', '终于', '到底', '究竟', '毕竟', '终究', '倒是', '反而', '其实', '实际上',
            '事实上', '确切地说', '严格来说', '广义地说', '狭义地说', '一般来说', '总的来说', '具体来说', '简单来说',
            '换句话说', '也就是说', '反之亦然', '相反地', '相比之下', '与此相比', '同样地', '类似地', '与此类似',
            '与之相反', '另一方面', '除此之外', '加之', '再者', '而且',
            '一起', '共同', '互相', '彼此', '相互', '一同', '一并', '一道', '协同',
            '合作', '配合', '协作', '协助', '帮助', '辅助', '支援', '支持', '赞助', '资助',
            '援助', '救援', '救济', '救助', '捐助', '捐赠', '馈赠', '赠送', '给予', '提供', '供应', '供给',
            '奉献', '贡献', '授予', '赋予', '赐予'
        }
        
        for feedback in feedbacks:
            content = feedback.get('content', '')
            # 简单分词（实际可以使用更复杂的分词库）
            words = content.split()
            for word in words:
                # 过滤掉停用词和短词
                if word not in stop_words and len(word) > 1:
                    word_count[word] = word_count.get(word, 0) + 1
        
        # 按词频排序，返回前10个关键词
        sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_words[:10]]
    
    def _generate_report(self, feedbacks: List[Dict], keywords: List[str]) -> Dict:
        """
        生成反馈分析报告
        
        Args:
            feedbacks: 反馈列表
            keywords: 关键词列表
            
        Returns:
            报告字典
        """
        report = {
            'total_count': len(feedbacks),
            'date_range': {
                'start': (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
                'end': datetime.now().strftime('%Y-%m-%d')
            },
            'keywords': keywords,
            'feedbacks': [
                {
                    'id': feedback.get('id'),
                    'rating': feedback.get('rating'),
                    'content': feedback.get('content'),
                    'created_at': feedback.get('created_at')
                } for feedback in feedbacks
            ]
        }
        return report
    
    async def _send_report_email(self, report: Dict):
        """
        发送分析报告邮件
        
        Args:
            report: 报告字典
        """
        # 实际实现可以使用邮件服务
        logger.info(f"发送反馈分析报告邮件，包含 {report['total_count']} 条低评分反馈")
        
        # 示例：如果有邮件服务，可以取消注释下面的代码
        # if self.mail_service:
        #     await self.mail_service.send_email(
        #         to='operation@example.com',
        #         subject=f'低评分反馈分析报告 ({report["date_range"]["start"]} 至 {report["date_range"]["end"]})',
        #         body=str(report)
        #     )
    
    def start_scheduler(self):
        """
        启动定时任务调度器
        """
        # 每天凌晨2点执行一次
        self.scheduler.add_job(
            self.analyze_low_rating_feedbacks,
            trigger=CronTrigger(hour=2, minute=0)
        )
        self.scheduler.start()
    
    def stop_scheduler(self):
        """
        停止定时任务调度器
        """
        self.scheduler.shutdown()
