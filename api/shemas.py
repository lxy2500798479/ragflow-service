"""
API请求和响应的模式定义
"""
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass

@dataclass
class ChatRequest:
    """聊天请求模式"""
    question: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

@dataclass
class ChatResponse:
    """聊天响应模式"""
    session_id: str
    answer: str
    error: bool = False
    ragflow_session_id: Optional[str] = None

@dataclass
class ErrorResponse:
    """错误响应模式"""
    error: str
    status_code: int = 400

@dataclass
class StatusResponse:
    """状态响应模式"""
    status: str
    message: str