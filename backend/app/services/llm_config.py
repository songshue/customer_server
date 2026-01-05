#!/usr/bin/env python3
"""
LLM配置管理 - 统一的LLM模型初始化
功能：从环境变量读取配置并初始化ChatOpenAI模型
"""
import os
import logging
from typing import Optional
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

logger = logging.getLogger(__name__)

# 全局单例实例
_llm_instance: Optional[ChatOpenAI] = None
_custom_llm_instances: dict = {}

def create_llm() -> Optional[ChatOpenAI]:
    """
    从环境变量创建LLM模型实例（单例模式）
    
    返回:
        ChatOpenAI: 配置好的LLM实例，如果配置不完整则返回None
    """
    global _llm_instance
    
    if _llm_instance is not None:
        return _llm_instance
    
    # 从环境变量读取配置
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")  # 默认模型
    
    if not api_key:
        logger.warning("未找到OPENAI_API_KEY配置")
        return None
    
    if not base_url:
        logger.warning("未找到OPENAI_BASE_URL配置")
        return None
    
    try:
        logger.info(f"初始化LLM模型: {model}")
        _llm_instance = ChatOpenAI(
            api_key=api_key,
            model=model,
            temperature=0.1,
            base_url=base_url,
            max_tokens=1000
        )
        return _llm_instance
    except Exception as e:
        logger.error(f"初始化LLM模型失败: {e}")
        return None

def create_llm_with_custom_config(
    temperature: float = 0.1,
    max_tokens: int = 1000,
    model: Optional[str] = None,
    **kwargs
) -> Optional[ChatOpenAI]:
    """
    使用自定义配置创建LLM模型实例（缓存机制）
    
    Args:
        temperature: 模型温度参数
        max_tokens: 最大token数
        model: 模型名称，如果为None则使用环境变量中的配置
        **kwargs: 其他ChatOpenAI参数
    
    返回:
        ChatOpenAI: 配置好的LLM实例
    """
    # 生成配置键用于缓存
    config_key = f"{model}_{temperature}_{max_tokens}_{str(sorted(kwargs.items()))}"
    
    if config_key in _custom_llm_instances:
        return _custom_llm_instances[config_key]
    
    # 从环境变量读取基础配置
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    default_model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    
    if not api_key:
        logger.warning("未找到OPENAI_API_KEY配置")
        return None
    
    if not base_url:
        logger.warning("未找到OPENAI_BASE_URL配置")
        return None
    
    # 使用传入的model或默认model
    model_name = model if model else default_model
    
    try:
        logger.info(f"初始化LLM模型: {model_name} (temperature={temperature})")
        instance = ChatOpenAI(
            api_key=api_key,
            model=model_name,
            temperature=temperature,
            base_url=base_url,
            max_tokens=max_tokens,
            **kwargs
        )
        _custom_llm_instances[config_key] = instance
        return instance
    except Exception as e:
        logger.error(f"初始化LLM模型失败: {e}")
        return None

def get_llm_instance() -> Optional[ChatOpenAI]:
    """
    获取单例LLM实例
    
    返回:
        ChatOpenAI: 单例LLM实例
    """
    return _llm_instance

def clear_llm_cache():
    """
    清除LLM实例缓存（主要用于测试）
    """
    global _llm_instance, _custom_llm_instances
    _llm_instance = None
    _custom_llm_instances.clear()
    logger.info("LLM实例缓存已清除")