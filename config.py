import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Config:
    """应用配置"""
    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-please-change-in-production')

    # Redis 配置
    REDIS_HOST = os.environ.get('REDIS_HOST', '127.0.0.1')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    REDIS_DB = int(os.environ.get('REDIS_DB', 0))
    REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', None)  # 如果Redis有密码

    # RagFlow会话在Redis中的过期时间（秒），例如1小时
    RAGFLOW_SESSION_EXPIRY_REDIS = int(os.environ.get('RAGFLOW_SESSION_EXPIRY_REDIS', 3600))

    # RagFlow配置
    RAGFLOW_API_KEY = os.environ.get('RAGFLOW_API_KEY', 'ragflow-I1NDJjN2MwMzQ4NTExZjA5NmI2NmEwYz')  # 添加默认值
    RAGFLOW_API_BASE = os.environ.get('RAGFLOW_API_BASE', 'https://ragflow.wy-ai.uk/api/v1')  # 添加默认值
    RAGFLOW_CHAT_ID = os.environ.get('RAGFLOW_CHAT_ID', '0db793303ae111f08d4b2aa20fe52986')  # 添加默认值

    BOT_WXID = os.environ.get('BOT_WXID', '')  # 添加默认值

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