"""
RagFlow工具函数
"""
import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def extract_title_from_first_message(message: str, max_length: int = 50) -> str:
    """
    从第一条消息中提取标题

    Args:
        message: 消息内容
        max_length: 最大长度

    Returns:
        提取的标题
    """
    # 移除特殊字符
    clean_message = re.sub(r'[^\w\s]', '', message)

    # 分割为单词
    words = clean_message.split()

    # 取前几个单词作为标题
    title_words = words[:10]  # 最多取10个单词
    title = ' '.join(title_words)

    # 截断到最大长度
    if len(title) > max_length:
        title = title[:max_length - 3] + '...'

    return title or "新对话"


def truncate_messages(messages: List[Dict[str, str]], max_tokens: int) -> List[Dict[str, str]]:
    """
    截断消息列表，使其不超过最大token数

    Args:
        messages: 消息列表
        max_tokens: 最大token数

    Returns:
        截断后的消息列表
    """
    # 简单实现：假设每个字符占用1个token
    # 实际应用中应使用更准确的token计数方法

    # 保留系统消息
    system_messages = [msg for msg in messages if msg.get('role') == 'system']
    other_messages = [msg for msg in messages if msg.get('role') != 'system']

    # 计算系统消息的token数
    system_tokens = sum(len(msg.get('content', '')) for msg in system_messages)

    # 计算剩余可用token数
    remaining_tokens = max_tokens - system_tokens

    # 如果剩余token不足，返回只包含系统消息的列表
    if remaining_tokens <= 0:
        logger.warning("系统消息已超过最大token数，无法包含其他消息")
        return system_messages

    # 从最新的消息开始，尽可能多地包含消息
    result = system_messages.copy()
    token_count = system_tokens

    for msg in reversed(other_messages):
        msg_tokens = len(msg.get('content', ''))
        if token_count + msg_tokens <= max_tokens:
            result.insert(len(system_messages), msg)  # 插入到系统消息之后
            token_count += msg_tokens
        else:
            break

    # 如果截断了消息，记录日志
    if len(result) < len(messages):
        logger.info(f"消息已截断，原始消息数: {len(messages)}，截断后: {len(result)}")

    return result