import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Config:
    """应用配置"""
    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-please-change-in-production')

    # RagFlow配置
    RAGFLOW_API_KEY = os.environ.get('RAGFLOW_API_KEY', 'ragflow-E4MGE2YzdlM2JiMjExZjA5MzAyMDI0Mm')  # 添加默认值
    RAGFLOW_API_BASE = os.environ.get('RAGFLOW_API_BASE', 'http://47.122.119.190:1180/api/v1')  # 添加默认值
    RAGFLOW_CHAT_ID = os.environ.get('RAGFLOW_CHAT_ID', '3881802a3bb411f0b42c0242ac120006')  # 添加默认值

    # 会话配置
    SESSION_EXPIRY = int(os.environ.get('SESSION_EXPIRY', 3600))  # 会话过期时间（秒）
    MAX_TOKENS = int(os.environ.get('MAX_TOKENS', 2500))  # 最大token数

    # 日志配置
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

    # 其他配置
    FALLBACK_REPLY = os.environ.get(
        'FALLBACK_REPLY',
        "您好，您问的这个问题我现在暂时无法给出完整的答复，为了能更好地帮到您，我帮您转接给人工客服同事进一步处理吧！"
    )