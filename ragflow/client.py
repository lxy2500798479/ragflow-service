import json
import requests
import logging
from typing import Dict, Any, Optional, Union

logger = logging.getLogger(__name__)


class RagFlowClient:
    """RagFlow API客户端"""

    def __init__(self, api_key: str, api_base: str, default_chat_id: str):
        """
        初始化RagFlow客户端

        Args:
            api_key: RagFlow API密钥
            api_base: RagFlow API基础URL
            default_chat_id: 默认聊天ID
        """
        self.api_key = api_key
        self.api_base = api_base
        self.default_chat_id = default_chat_id

        if not all([self.api_key, self.api_base, self.default_chat_id]):
            logger.error("RagFlow API 密钥、基础URL或默认chat_id未配置。")
            raise ValueError("RagFlow 配置缺失。")

        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

        logger.info("RagFlow API 客户端已初始化。")

    def create_session(self, chat_id: str, title: str) -> Optional[str]:
        """
        创建一个新的RagFlow会话

        Args:
            chat_id: 聊天ID
            title: 会话标题

        Returns:
            会话ID，如果创建失败则返回None
        """
        url = f"{self.api_base}/chats/{chat_id}/sessions"
        payload = {"name": title}

        logger.debug(f"正在创建RagFlow会话。URL: {url}, 标题: {title}")

        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=10)
            response.raise_for_status()
            res_data = response.json()

            if res_data.get("code") == 0:
                session_id = res_data.get("data", {}).get("id")
                logger.info(f"RagFlow会话已创建。ID: {session_id}, 标题: {title}")
                return session_id
            else:
                logger.error(f"创建RagFlow会话失败: {res_data.get('message')}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"创建RagFlow会话时发生异常: {e}")
            return None

    def send_message(self,
                     question: str,
                     session_id: str,
                     chat_id: Optional[str] = None,
                     stream: bool = False,
                     timeout: int = 60) -> Dict[str, Any]:
        """
        发送消息到RagFlow

        Args:
            question: 用户问题
            session_id: 会话ID
            chat_id: 聊天ID，如果为None则使用默认值
            stream: 是否使用流式响应
            timeout: 请求超时时间（秒）

        Returns:
            包含响应内容的字典
        """
        chat_id_to_use = chat_id or self.default_chat_id

        payload = {
            "question": question,
            "session_id": session_id,
            "stream": stream,
        }

        url = f"{self.api_base}/chats/{chat_id_to_use}/completions"
        logger.debug(f"发送消息到RagFlow。URL: {url}, 负载: {json.dumps(payload)}")

        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=timeout)
            response.raise_for_status()

            res_data = response.json()
            logger.debug(f"RagFlow响应: {json.dumps(res_data, ensure_ascii=False)}")

            if res_data.get("code") == 0:
                data_payload = res_data.get("data", {})
                if isinstance(data_payload, dict):
                    answer = data_payload.get("answer", "")
                    return {
                        "content": answer.strip(),
                        "error": False,
                        "session_id": session_id
                    }

            logger.error(f"RagFlow API返回错误码: {res_data.get('code')}, 消息: {res_data.get('message')}")
            return {
                "content": f"服务返回错误: {res_data.get('message', '未知错误')}",
                "error": True,
                "session_id": session_id
            }

        except requests.exceptions.Timeout:
            logger.error(f"RagFlow请求超时")
            return {"content": "请求超时，请稍后再试。", "error": True, "session_id": session_id}

        except requests.exceptions.HTTPError as e:
            logger.error(f"RagFlow HTTP错误: {e.response.status_code} - {e.response.text}")
            error_content = f"服务通讯失败 (HTTP {e.response.status_code})。"

            try:
                err_json = e.response.json()
                if err_json.get("message"):
                    error_content = f"服务通讯失败: {err_json.get('message')}"
            except json.JSONDecodeError:
                pass

            return {"content": error_content, "error": True, "session_id": session_id}

        except Exception as e:
            logger.error(f"发送消息到RagFlow时发生异常: {e}")
            return {"content": "处理您的请求时发生未知错误。", "error": True, "session_id": session_id}