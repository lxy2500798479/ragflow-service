import logging
import time
from typing import Dict, Any, Optional, List, Union

from ragflow.client import RagFlowClient
from ragflow.session import SessionManager, RagFlowSession

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, api_key, api_base, default_chat_id, session_expiry=3600, max_tokens=2500, fallback_reply=None):
        """
        初始化聊天服务

        Args:
            api_key: RagFlow API密钥
            api_base: RagFlow API基础URL
            default_chat_id: 默认聊天ID
            session_expiry: 会话过期时间（秒）
            max_tokens: 最大token数
            fallback_reply: 回退回复
        """
        self.ragflow_client = RagFlowClient(api_key, api_base, default_chat_id)
        self.default_chat_id = default_chat_id
        self.session_manager = SessionManager(expiry_seconds=session_expiry)
        self.max_tokens = max_tokens
        self.fallback_reply = fallback_reply

        # 存储微信ID到RagFlow会话ID的映射
        self.wxid_to_session = {}

        logger.info("聊天服务已初始化")

    def get_or_create_session(self, wxid, is_group=False):
        """
        获取或创建会话

        Args:
            wxid: 微信ID（用户ID或群ID）
            is_group: 是否为群聊

        Returns:
            RagFlow会话ID
        """
        # 检查是否已有映射
        if wxid in self.wxid_to_session:
            # 获取现有会话
            session_id = self.wxid_to_session[wxid]
            logger.info(f"使用现有会话: {wxid} -> {session_id}")
            return session_id

        # 创建新会话
        # 为会话创建标题
        if is_group:
            title = f"群聊 {wxid[:8]}"
        else:
            title = f"私聊 {wxid[:8]}"

        # 创建RagFlow会话
        ragflow_session_id = self.ragflow_client.create_session(
            chat_id=self.default_chat_id,
            title=title
        )

        if not ragflow_session_id:
            logger.error(f"创建RagFlow会话失败，微信ID: {wxid}")
            return None

        # 保存映射
        self.wxid_to_session[wxid] = ragflow_session_id
        logger.info(f"创建新会话: {wxid} -> {ragflow_session_id}")

        return ragflow_session_id

    def process_wechat_message(self, question, wxid, user_id=None, is_group=False, context=None):
        """
        处理微信消息

        Args:
            question: 问题
            wxid: 微信ID（用户ID或群ID）
            user_id: 用户ID（在群聊中是发送者ID）
            is_group: 是否为群聊
            context: 上下文信息

        Returns:
            处理结果
        """
        if context is None:
            context = {}

        # 获取或创建RagFlow会话
        ragflow_session_id = self.get_or_create_session(wxid, is_group)

        if not ragflow_session_id:
            return {
                "content": "创建会话失败，请稍后再试。",
                "error": True
            }

        # 发送消息到RagFlow
        response = self.ragflow_client.send_message(
            question=question,
            session_id=ragflow_session_id,
            chat_id=self.default_chat_id
        )

        # 处理响应
        if response.get("error"):
            logger.error(f"RagFlow响应错误: {response.get('error_message')}")
            return {
                "content": self.fallback_reply or "抱歉，我无法回答这个问题。",
                "error": True,
                "ragflow_session_id": ragflow_session_id
            }

        return {
            "content": response.get("content", ""),
            "error": False,
            "ragflow_session_id": ragflow_session_id
        }

    def clear_wechat_session(self, wxid):
        """
        清除微信会话

        Args:
            wxid: 微信ID

        Returns:
            是否成功
        """
        if wxid in self.wxid_to_session:
            ragflow_session_id = self.wxid_to_session[wxid]
            # 可以选择在RagFlow中删除会话
            # self.ragflow_client.delete_session(ragflow_session_id)

            # 删除映射
            del self.wxid_to_session[wxid]
            logger.info(f"已清除会话: {wxid} -> {ragflow_session_id}")
            return True

        return False

    def clear_all_wechat_sessions(self):
        """
        清除所有微信会话
        """
        # 可以选择在RagFlow中删除所有会话
        # for session_id in self.wxid_to_session.values():
        #     self.ragflow_client.delete_session(session_id)

        # 清空映射
        self.wxid_to_session.clear()
        logger.info("已清除所有微信会话")