#!/usr/bin/env python3
"""
创建示例PDF政策文档（使用 Windows 自带中文字体）
"""
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

def create_policy_pdf():
    """创建支持中文的政策PDF文档，使用 Windows 自带黑体"""
    # 确保 knowledge 目录存在
    os.makedirs("knowledge", exist_ok=True)
    pdf_path = "knowledge/policy.pdf"
    
    # 创建PDF文档
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter
    
    # 注册 Windows 自带黑体字体（SimHei）
    try:
        # Windows 字体路径
        font_path = r"C:\Windows\Fonts\simhei.ttf"
        pdfmetrics.registerFont(TTFont("SimHei", font_path))
        print("✅ 成功加载 Windows 黑体字体")
    except Exception as e:
        print(f"❌ 无法加载黑体字体，请确保在 Windows 系统运行: {e}")
        return

    # 设置默认字体为黑体
    c.setFont("SimHei", 12)

    y_position = height - 50
    line_height = 20

    policies = [
        "第一章 服务宗旨",
        "1.1 我们的服务宗旨是以客户为中心，提供优质、高效的服务体验。",
        "1.2 致力于快速响应客户需求，解决客户问题。",
        "",
        "第二章 服务时间",
        "2.1 在线客服时间：工作日 9:00-18:00",
        "2.2 紧急情况24小时响应机制",
        "2.3 节假日期间提供值班服务",
        "",
        "第三章 服务标准",
        "3.1 响应时间：在线客服3分钟内响应",
        "3.2 处理时效：一般问题24小时内解决",
        "3.3 服务态度：专业、友好、耐心",
        "",
        "第四章 客户权益",
        "4.1 客户有权获得及时、准确的信息回复",
        "4.2 客户有权要求服务记录和跟进",
        "4.3 客户有权对服务质量进行评价",
        "",
        "第五章 投诉处理",
        "5.1 投诉渠道：在线客服、电话、邮箱",
        "5.2 投诉处理时限：3个工作日内给出回复",
        "5.3 投诉处理标准：公平、公正、透明",
        "",
        "第六章 隐私保护",
        "6.1 严格保护客户个人信息",
        "6.2 未经授权不泄露客户信息",
        "6.3 定期进行隐私安全培训",
        "",
        "本政策自2026年1月1日起执行，最终解释权归公司所有。"
    ]

    for policy in policies:
        if y_position < 50:  # 换页
            c.showPage()
            c.setFont("SimHei", 12)
            y_position = height - 50

        if policy.startswith("第") and "章" in policy:
            # 章节标题：加粗（用黑体本身已较粗，或可换更大字号）
            c.setFont("SimHei", 14)
            c.drawString(50, y_position, policy)
            c.setFont("SimHei", 12)
        elif policy.startswith(("1.", "2.", "3.", "4.", "5.", "6.")):
            # 小节内容，缩进
            c.drawString(70, y_position, policy)
        else:
            # 普通段落
            c.drawString(50, y_position, policy)

        y_position -= line_height

    # 保存PDF
    c.save()
    print(f"✅ PDF文档已成功创建：{os.path.abspath(pdf_path)}")

if __name__ == "__main__":
    create_policy_pdf()