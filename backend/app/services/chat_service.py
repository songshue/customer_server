import random
import re
from typing import Dict, List, Tuple

class ChatService:
    """智能客服聊天服务"""
    
    def __init__(self):
        """初始化聊天服务"""
        self.setup_response_rules()
    
    def setup_response_rules(self):
        """设置回复规则"""
        
        # 问候语回复
        self.greeting_responses = [
            "您好！欢迎使用我们的客服系统，我是智能客服助手，很高兴为您服务。请问有什么可以帮助您的吗？",
            "Hello！很高兴为您提供帮助。请告诉我您遇到了什么问题，我会尽力为您解决。",
            "您好！我是您的专属客服，有任何问题都可以随时咨询我哦~",
            "欢迎光临！我是智能客服小助手，请输入您的问题，我将为您提供专业服务。"
        ]
        
        # 商品咨询相关回复
        self.product_responses = {
            'phone': [
                "我们主营各类智能手机，包括iPhone、华为、小米、OPPO、vivo等知名品牌。所有商品均为正品行货，支持全国联保。",
                "手机产品方面，我们有最新款的iPhone 15系列、华为Mate60系列、小米14系列等热销机型。您想了解哪款呢？",
                "手机价格从千元机到旗舰机都有，不同价位满足您的需求。需要我为您推荐合适的机型吗？"
            ],
            'computer': [
                "我们提供各类笔记本电脑，包括游戏本、商务本、轻薄本等。品牌涵盖联想、戴尔、惠普、华硕等。",
                "电脑产品方面，我们有联想ThinkPad系列、戴尔XPS系列、惠普暗影精灵游戏本等优质产品。",
                "台式机方面，我们提供组装机和品牌机两种选择，可以根据您的需求定制配置。"
            ],
            'tablet': [
                "平板电脑产品有iPad系列、华为MatePad系列、小米平板等。适合办公、学习、娱乐等多种场景。",
                "我们的平板产品支持手写笔输入，可以满足您的办公和学习需求。",
                "平板价格从千元入门级到高端旗舰级都有，您可以根据使用需求选择合适的型号。"
            ]
        }
        
        # 价格咨询回复
        self.price_responses = [
            "关于价格，不同品牌和型号的产品价格差异较大。建议您先确定具体的产品型号，我可以为您查询最新的价格信息。",
            "我们的产品价格都是市场竞争力价格，支持多种支付方式。您可以告诉我具体想了解哪个产品的价格吗？",
            "价格会根据促销活动和库存情况有所变动，建议您关注我们的官方活动页面获取最新价格。"
        ]
        
        # 物流配送回复
        self.logistics_responses = [
            "我们支持全国包邮，一般3-7个工作日送达，偏远地区可能需要5-10个工作日。",
            "物流信息可以通过订单号查询，我们会及时更新发货状态和物流信息。",
            "紧急订单支持顺丰快递，次日达服务（部分城市），但需要额外支付快递费用。"
        ]
        
        # 售后服务回复
        self.service_responses = [
            "我们提供7天无理由退货，15天换货，终身保修服务。具体保修政策根据产品不同有所差异。",
            "如果您收到商品后发现质量问题，请及时联系客服，我们会协助您处理退换货事宜。",
            "售后服务热线：400-123-4567，工作时间：周一至周日 9:00-21:00。"
        ]
        
        # 支付方式回复
        self.payment_responses = [
            "我们支持支付宝、微信支付、银行卡刷卡、信用卡分期等多种支付方式。",
            "大额商品支持分期付款，12期免息，让您购物更轻松。",
            "首次购买用户还有新用户专享优惠，欢迎使用！"
        ]
        
        # 优惠活动回复
        self.promotion_responses = [
            "我们经常举办各种促销活动，包括满减、折扣、买一送一等。您可以关注我们的官方微信获取最新活动信息。",
            "当前正在进行的新用户注册送优惠券活动，购物满500元可减50元！",
            "每月15日是我们的会员日，会员专享折扣和积分翻倍活动，不容错过！"
        ]
        
        # 投诉建议回复
        self.complaint_responses = [
            "非常抱歉给您带来不好的体验，我会立即将您的问题反馈给相关部门。我们重视每一位用户的意见和建议。",
            "您的反馈对我们很重要，我们会认真处理并改进服务。如果需要人工客服介入，我也可以为您转接。",
            "投诉建议请发送至 feedback@company.com 或拨打客服热线400-123-4567，我们会在24小时内回复您。"
        ]
        
        # 感谢回复
        self.thanks_responses = [
            "不客气！很高兴能帮助到您。如果还有其他问题，随时欢迎您咨询！",
            "不用谢，为您服务是我们的荣幸。祝您生活愉快，购物愉快！",
            "很高兴为您解决问题！如果需要帮助，请随时联系我们。"
        ]
        
        # 道歉回复
        self.apology_responses = [
            "真的很抱歉给您带来困扰，我会努力改进服务，希望能为您提供更好的体验。",
            "对不起让您不满意，我们一定认真反思并改进。请给我们一次改进的机会。",
            "非常抱歉，我们理解您的心情，请让我们用更好的服务来弥补这次的不足。"
        ]
        
        # 退出语回复
        self.farewell_responses = [
            "感谢您的咨询，祝您生活愉快！如果需要帮助，随时欢迎回来。",
            "再见！祝您购物愉快，生活美满！期待下次为您服务。",
            "感谢使用我们的客服系统，祝您一切顺利！"
        ]
        
        # 默认回复
        self.default_responses = [
            "抱歉，我暂时没有理解您的问题。您可以尝试换个说法，或者选择以下关键词：商品咨询、价格、物流、售后、支付、优惠等。",
            "这个问题我还在学习中，您可以具体描述一下您的需求，或者联系人工客服获得更专业的帮助。",
            "我没有完全理解您的意思，请问您是想了解：1)商品信息 2)价格咨询 3)物流配送 4)售后服务 5)支付方式 呢？",
            "很抱歉，我没有找到相关的信息。您可以重新描述您的问题，或者提供更多细节吗？"
        ]
        
        # 关键词匹配规则
        self.keyword_rules = {
            'greeting': ['你好', '您好', 'hello', 'hi', '在吗', '在不在', '在么'],
            'phone': ['手机', 'phone', 'iphone', '华为', '小米', 'oppo', 'vivo'],
            'computer': ['电脑', 'computer', '笔记本', '台式机', '联想', '戴尔', '惠普', '华硕'],
            'tablet': ['平板', 'tablet', 'ipad', 'matepad'],
            'price': ['价格', '多少钱', 'price', '费用', '贵', '便宜', '优惠', '打折', '促销'],
            'logistics': ['物流', '快递', '配送', '发货', '到货', '时间', '几天'],
            'service': ['售后', '保修', '退货', '换货', '维修', '服务'],
            'payment': ['支付', '付款', '支付宝', '微信', '银行卡', '分期'],
            'promotion': ['活动', '优惠', '折扣', '促销', '特价', '便宜'],
            'complaint': ['投诉', '建议', '意见', '不满', '差评', '问题'],
            'thanks': ['谢谢', '感谢', '多谢', '不用谢', '辛苦了'],
            'apology': ['抱歉', '对不起', '不好意思', '错怪了'],
            'farewell': ['再见', '拜拜', '好了', '就这样', '结束']
        }
    
    def get_response(self, user_message: str) -> str:
        """
        根据用户消息生成回复
        
        Args:
            user_message: 用户输入的消息
            
        Returns:
            生成的回复消息
        """
        user_message = user_message.lower().strip()
        
        # 提取关键词并分类
        matched_categories = self._extract_keywords(user_message)
        
        # 根据匹配的类别生成回复
        response = self._generate_response(matched_categories)
        
        return response
    
    def _extract_keywords(self, message: str) -> List[str]:
        """提取消息中的关键词并分类"""
        matched_categories = []
        
        for category, keywords in self.keyword_rules.items():
            for keyword in keywords:
                if keyword in message:
                    matched_categories.append(category)
                    break
        
        return matched_categories
    
    def _generate_response(self, categories: List[str]) -> str:
        """根据匹配的类别生成回复"""
        
        if not categories:
            # 没有匹配到任何关键词，使用默认回复
            return random.choice(self.default_responses)
        
        # 按优先级处理不同类型的消息
        priority_order = [
            'greeting', 'farewell', 'thanks', 'apology', 'complaint',
            'phone', 'computer', 'tablet', 'price', 'logistics', 
            'service', 'payment', 'promotion'
        ]
        
        for category in priority_order:
            if category in categories:
                return self._get_category_response(category)
        
        # 如果没有匹配到优先级中的类别，使用第一个匹配的类别
        return self._get_category_response(categories[0])
    
    def _get_category_response(self, category: str) -> str:
        """获取特定类别的回复"""
        
        if category == 'greeting':
            return random.choice(self.greeting_responses)
        elif category == 'phone':
            return random.choice(self.product_responses['phone'])
        elif category == 'computer':
            return random.choice(self.product_responses['computer'])
        elif category == 'tablet':
            return random.choice(self.product_responses['tablet'])
        elif category == 'price':
            return random.choice(self.price_responses)
        elif category == 'logistics':
            return random.choice(self.logistics_responses)
        elif category == 'service':
            return random.choice(self.service_responses)
        elif category == 'payment':
            return random.choice(self.payment_responses)
        elif category == 'promotion':
            return random.choice(self.promotion_responses)
        elif category == 'complaint':
            return random.choice(self.complaint_responses)
        elif category == 'thanks':
            return random.choice(self.thanks_responses)
        elif category == 'apology':
            return random.choice(self.apology_responses)
        elif category == 'farewell':
            return random.choice(self.farewell_responses)
        else:
            return random.choice(self.default_responses)