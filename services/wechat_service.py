import requests
import logging
import json
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class WeChatService:
    """微信服务，用于与微信HTTP API交互"""

    def __init__(self, api_base: str = "http://127.0.0.1:8888/wechat/httpapi"):
        """
        初始化微信服务

        Args:
            api_base: 微信HTTP API基础URL
        """
        self.api_base = api_base
        logger.info(f"微信服务已初始化，API基础URL: {api_base}")

    def send_text_message(self, to_wxid: str, content: str, at_list: Optional[list] = None) -> Dict[str, Any]:
        """
        发送文本消息

        Args:
            to_wxid: 接收者wxid (用户ID或群ID)
            content: 消息内容
            at_list: 需要@的用户列表 (仅群聊有效)

        Returns:
            API响应
        """
        url = f"{self.api_base}"

        # 根据新的API格式构建payload
        payload = {
            "type": "sendText2",
            "data": {
                "wxid": to_wxid,
                "msg": content,
                "compatible": "0"
            }
        }

        # 如果需要在消息中添加@用户，可以在content中添加特殊格式
        # 例如: "你好[@,wxid=wxid_123456,nick=用户昵称,isAuto=true]"
        # 或者使用 @all: "[@,wxid=all,nick=所有人,isAuto=true]"

        logger.debug(f"发送微信消息: {json.dumps(payload, ensure_ascii=False)}")

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()

            logger.info(f"微信消息发送结果: {json.dumps(result, ensure_ascii=False)}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"发送微信消息失败: {e}")
            return {"status": "error", "message": str(e)}

    def send_image(self, to_wxid: str, image_path: str) -> Dict[str, Any]:
        """
        发送图片消息

        Args:
            to_wxid: 接收者wxid
            image_path: 图片路径

        Returns:
            API响应
        """
        url = f"{self.api_base}"

        payload = {
            "event": 10009,
            "data": {
                "type": "sendMsg",
                "des": "发送消息",
                "data": {
                    "toWxid": to_wxid,
                    "msg": image_path,
                    "msgType": 3  # 3=图片消息
                }
            }
        }

        logger.debug(f"发送微信图片: {json.dumps(payload, ensure_ascii=False)}")

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()

            logger.info(f"微信图片发送结果: {json.dumps(result, ensure_ascii=False)}")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"发送微信图片失败: {e}")
            return {"status": "error", "message": str(e)}