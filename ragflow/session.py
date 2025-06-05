import time
import logging
from typing import Dict, Any, Optional, List, Union

logger = logging.getLogger(__name__)


class Session:
    """基础会话类"""

    def __init__(self, session_id: str, system_prompt: Optional[str] = None):
        """
        初始化会话

        Args:
            session_id: 会话ID
            system_prompt: 系统提示
        """
        self.session_id = session_id
        self.system_prompt = system_prompt
        self.messages = []

        # 如果有系统提示，添加为第一条消息
        if system_prompt:
            self.messages.append({"role": "system", "content": system_prompt})

    def add_message(self, role: str, content: str) -> None:
        """
        添加消息到会话

        Args:
            role: 消息角色 (user/assistant)
            content: 消息内容
        """
        self.messages.append({"role": role, "content": content})

    def get_messages(self) -> List[Dict[str, str]]:
        """获取所有消息"""
        return self.messages

    def reset(self) -> None:
        """重置会话，保留系统提示"""
        if self.system_prompt:
            self.messages = [{"role": "system", "content": self.system_prompt}]
        else:
            self.messages = []


class RagFlowSession(Session):
    """RagFlow会话类"""

    def __init__(self, session_id: str, system_prompt: Optional[str] = None,
                 ragflow_chat_id: Optional[str] = None):
        """
        初始化RagFlow会话

        Args:
            session_id: 会话ID
            system_prompt: 系统提示
            ragflow_chat_id: RagFlow聊天ID
        """
        super().__init__(session_id, system_prompt)
        self.ragflow_chat_id = ragflow_chat_id
        self.ragflow_session_id = None
        self.custom_title_set = False
        self.created_at = time.time()
        self.last_active = time.time()

    def set_ragflow_session(self, session_id: str, title_was_set: bool = True) -> None:
        """
        设置RagFlow会话ID

        Args:
            session_id: RagFlow会话ID
            title_was_set: 是否已设置标题
        """
        self.ragflow_session_id = session_id
        self.custom_title_set = title_was_set

    def get_ragflow_session_id(self) -> Optional[str]:
        """获取RagFlow会话ID"""
        return self.ragflow_session_id

    def has_custom_title_been_set(self) -> bool:
        """检查是否已设置自定义标题"""
        return self.custom_title_set

    def update_last_active(self) -> None:
        """更新最后活动时间"""
        self.last_active = time.time()

    def is_expired(self, expiry_seconds: int) -> bool:
        """
        检查会话是否已过期

        Args:
            expiry_seconds: 过期时间（秒）

        Returns:
            是否已过期
        """
        return (time.time() - self.last_active) > expiry_seconds


class SessionManager:
    """会话管理器"""

    def __init__(self, expiry_seconds: int = 3600):
        """
        初始化会话管理器

        Args:
            expiry_seconds: 会话过期时间（秒）
        """
        self.sessions: Dict[str, RagFlowSession] = {}
        self.expiry_seconds = expiry_seconds
        logger.info(f"会话管理器已初始化，会话过期时间: {expiry_seconds}秒")

    def get_session(self, session_id: str, system_prompt: Optional[str] = None,
                    ragflow_chat_id: Optional[str] = None) -> RagFlowSession:
        """
        获取会话，如果不存在则创建

        Args:
            session_id: 会话ID
            system_prompt: 系统提示
            ragflow_chat_id: RagFlow聊天ID

        Returns:
            会话对象
        """
        # 清理过期会话
        self._cleanup_expired_sessions()

        # 如果会话不存在，创建新会话
        if session_id not in self.sessions:
            logger.info(f"创建新会话: {session_id}")
            self.sessions[session_id] = RagFlowSession(session_id, system_prompt, ragflow_chat_id)

        # 更新最后活动时间
        self.sessions[session_id].update_last_active()

        return self.sessions[session_id]

    def clear_session(self, session_id: str) -> bool:
        """
        清除会话

        Args:
            session_id: 会话ID

        Returns:
            是否成功清除
        """
        if session_id in self.sessions:
            logger.info(f"清除会话: {session_id}")
            del self.sessions[session_id]
            return True
        return False

    def clear_all_sessions(self) -> None:
        """清除所有会话"""
        logger.info("清除所有会话")
        self.sessions.clear()

    def _cleanup_expired_sessions(self) -> None:
        """清理过期会话"""
        current_time = time.time()
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if (current_time - session.last_active) > self.expiry_seconds
        ]

        for session_id in expired_sessions:
            logger.info(f"会话已过期，正在清除: {session_id}")
            del self.sessions[session_id]