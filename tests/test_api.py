import json
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app


class TestAPI(unittest.TestCase):
    """API测试类"""

    def setUp(self):
        """测试前准备"""
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

        # 模拟服务初始化
        self.chat_service_mock = MagicMock()
        self.app.extensions['chat_service'] = self.chat_service_mock

    @patch('services.chat_service.ChatService')
    def test_chat_endpoint(self, mock_chat_service):
        """测试聊天接口"""
        # 设置模拟返回值
        mock_instance = mock_chat_service.return_value
        mock_instance.process_message.return_value = {
            "content": "这是一个测试回复",
            "error": False,
            "ragflow_session_id": "test-session-123"
        }

        # 发送请求
        response = self.client.post(
            '/api/chat',
            data=json.dumps({
                "question": "这是一个测试问题",
                "session_id": "test-session-id",
                "user_id": "test-user"
            }),
            content_type='application/json'
        )

        # 验证响应
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['answer'], "这是一个测试回复")
        self.assertEqual(data['session_id'], "test-session-id")
        self.assertEqual(data['error'], False)
        self.assertEqual(data['ragflow_session_id'], "test-session-123")

        # 验证服务调用
        mock_instance.process_message.assert_called_once_with(
            question="这是一个测试问题",
            session_id="test-session-id",
            user_id="test-user",
            context=None
        )

    @patch('services.chat_service.ChatService')
    def test_clear_session_endpoint(self, mock_chat_service):
        """测试清除会话接口"""
        # 设置模拟返回值
        mock_instance = mock_chat_service.return_value
        mock_instance.clear_session.return_value = True

        # 发送请求
        response = self.client.delete('/api/sessions/test-session-id')

        # 验证响应
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], "success")
        self.assertEqual(data['message'], "会话已清除")

        # 验证服务调用
        mock_instance.clear_session.assert_called_once_with("test-session-id")

    @patch('services.chat_service.ChatService')
    def test_clear_all_sessions_endpoint(self, mock_chat_service):
        """测试清除所有会话接口"""
        # 设置模拟返回值
        mock_instance = mock_chat_service.return_value

        # 发送请求
        response = self.client.delete('/api/sessions')

        # 验证响应
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], "success")
        self.assertEqual(data['message'], "所有会话已清除")

        # 验证服务调用
        mock_instance.clear_all_sessions.assert_called_once()


if __name__ == '__main__':
    unittest.main()