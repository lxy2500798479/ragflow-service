import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import time

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ragflow.client import RagFlowClient
from ragflow.session import SessionManager, RagFlowSession


class TestRagFlowClient(unittest.TestCase):
    """RagFlow客户端测试类"""

    def setUp(self):
        """测试前准备"""
        self.api_key = "test-api-key"
        self.api_base = "https://api.example.com"
        self.default_chat_id = "test-chat-id"

        # 创建客户端实例
        self.client = RagFlowClient(self.api_key, self.api_base, self.default_chat_id)

    @patch('requests.post')
    def test_create_session(self, mock_post):
        """测试创建会话"""
        # 设置模拟响应
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "id": "test-session-123"
            }
        }
        mock_post.return_value = mock_response

        # 调用方法
        session_id = self.client.create_session("test-chat-id", "Test Session")

        # 验证结果
        self.assertEqual(session_id, "test-session-123")

        # 验证请求
        mock_post.assert_called_once_with(
            f"{self.api_base}/chats/test-chat-id/sessions",
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            },
            json={"name": "Test Session"},
            timeout=10
        )

    @patch('requests.post')
    def test_send_message(self, mock_post):
        """测试发送消息"""
        # 设置模拟响应
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "answer": "这是一个测试回复"
            }
        }
        mock_post.return_value = mock_response

        # 调用方法
        result = self.client.send_message(
            question="这是一个测试问题",
            session_id="test-session-id"
        )

        # 验证结果
        self.assertEqual(result["content"], "这是一个测试回复")
        self.assertEqual(result["error"], False)

        # 验证请求
        mock_post.assert_called_once_with(
            f"{self.api_base}/chats/{self.default_chat_id}/completions",
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            },
            json={
                "question": "这是一个测试问题",
                "session_id": "test-session-id",
                "stream": False
            },
            timeout=60
        )


class TestSessionManager(unittest.TestCase):
    """会话管理器测试类"""

    def setUp(self):
        """测试前准备"""
        self.session_manager = SessionManager(expiry_seconds=1)  # 设置较短的过期时间便于测试

    def test_get_session(self):
        """测试获取会话"""
        # 获取不存在的会话（应创建新会话）
        session = self.session_manager.get_session("test-session-id")

        # 验证结果
        self.assertIsInstance(session, RagFlowSession)
        self.assertEqual(session.session_id, "test-session-id")

        # 再次获取同一会话
        same_session = self.session_manager.get_session("test-session-id")

        # 验证是同一个会话对象
        self.assertIs(session, same_session)

    def test_clear_session(self):
        """测试清除会话"""
        # 创建会话
        self.session_manager.get_session("test-session-id")

        # 清除会话
        result = self.session_manager.clear_session("test-session-id")

        # 验证结果
        self.assertTrue(result)

        # 验证会话已被清除
        self.assertNotIn("test-session-id", self.session_manager.sessions)

        # 尝试清除不存在的会话
        result = self.session_manager.clear_session("non-existent-session")

        # 验证结果
        self.assertFalse(result)

    def test_clear_all_sessions(self):
        """测试清除所有会话"""
        # 创建多个会话
        self.session_manager.get_session("test-session-1")
        self.session_manager.get_session("test-session-2")

        # 清除所有会话
        self.session_manager.clear_all_sessions()

        # 验证所有会话已被清除
        self.assertEqual(len(self.session_manager.sessions), 0)

    def test_session_expiry(self):
        """测试会话过期"""
        # 创建会话
        self.session_manager.get_session("test-session-id")

        # 等待会话过期
        time.sleep(1.5)

        # 获取新会话（应触发清理过期会话）
        self.session_manager.get_session("another-session-id")

        # 验证过期会话已被清除
        self.assertNotIn("test-session-id", self.session_manager.sessions)
        self.assertIn("another-session-id", self.session_manager.sessions)


class TestRagFlowSession(unittest.TestCase):
    """RagFlow会话测试类"""

    def setUp(self):
        """测试前准备"""
        self.session = RagFlowSession(
            session_id="test-session-id",
            system_prompt="这是一个系统提示",
            ragflow_chat_id="test-chat-id"
        )

    def test_initialization(self):
        """测试初始化"""
        # 验证初始状态
        self.assertEqual(self.session.session_id, "test-session-id")
        self.assertEqual(self.session.system_prompt, "这是一个系统提示")
        self.assertEqual(self.session.ragflow_chat_id, "test-chat-id")
        self.assertIsNone(self.session.ragflow_session_id)
        self.assertFalse(self.session.custom_title_set)

        # 验证系统提示已添加到消息列表
        self.assertEqual(len(self.session.messages), 1)
        self.assertEqual(self.session.messages[0]["role"], "system")
        self.assertEqual(self.session.messages[0]["content"], "这是一个系统提示")

    def test_add_message(self):
        """测试添加消息"""
        # 添加用户消息
        self.session.add_message("user", "这是一个用户消息")

        # 验证消息已添加
        self.assertEqual(len(self.session.messages), 2)
        self.assertEqual(self.session.messages[1]["role"], "user")
        self.assertEqual(self.session.messages[1]["content"], "这是一个用户消息")

        # 添加助手消息
        self.session.add_message("assistant", "这是一个助手消息")

        # 验证消息已添加
        self.assertEqual(len(self.session.messages), 3)
        self.assertEqual(self.session.messages[2]["role"], "assistant")
        self.assertEqual(self.session.messages[2]["content"], "这是一个助手消息")

    def test_set_ragflow_session(self):
        """测试设置RagFlow会话ID"""
        # 设置RagFlow会话ID
        self.session.set_ragflow_session("ragflow-session-123", True)

        # 验证结果
        self.assertEqual(self.session.ragflow_session_id, "ragflow-session-123")
        self.assertTrue(self.session.custom_title_set)

    def test_reset(self):
        """测试重置会话"""
        # 添加一些消息
        self.session.add_message("user", "用户消息")
        self.session.add_message("assistant", "助手消息")

        # 重置会话
        self.session.reset()

        # 验证只保留了系统提示
        self.assertEqual(len(self.session.messages), 1)
        self.assertEqual(self.session.messages[0]["role"], "system")
        self.assertEqual(self.session.messages[0]["content"], "这是一个系统提示")

    def test_is_expired(self):
        """测试会话过期检查"""
        # 新会话不应过期
        self.assertFalse(self.session.is_expired(3600))

        # 修改最后活动时间
        self.session.last_active = time.time() - 7200  # 2小时前

        # 现在应该过期
        self.assertTrue(self.session.is_expired(3600))


if __name__ == '__main__':
    unittest.main()