from flask import Blueprint, request, jsonify, current_app
import logging
import uuid

from api.shemas import StatusResponse, ErrorResponse, ChatResponse, ChatRequest
from services.chat_service import ChatService

logger = logging.getLogger(__name__)
api_bp = Blueprint('api', __name__)

# 创建聊天服务实例
chat_service = None


@api_bp.before_app_request
def initialize_services():
    """初始化服务"""
    global chat_service

    config = current_app.config
    logger.info(f"配置: {config}")
    chat_service = ChatService(
        api_key=config['RAGFLOW_API_KEY'],
        api_base=config['RAGFLOW_API_BASE'],
        default_chat_id=config['RAGFLOW_CHAT_ID'],
        session_expiry=config['SESSION_EXPIRY'],
        max_tokens=config['MAX_TOKENS'],
        fallback_reply=config['FALLBACK_REPLY']
    )
    logger.info("聊天服务已初始化")


@api_bp.route('/chat', methods=['POST'])
def chat():
    """聊天接口"""
    try:
        data = request.json

        # 验证请求数据
        if not data:
            error_response = ErrorResponse(error="无效的请求数据", status_code=400)
            return jsonify(error_response.__dict__), 400

        # 使用ChatRequest数据类解析请求
        try:
            chat_request = ChatRequest(
                question=data.get('question', ''),
                session_id=data.get('session_id'),
                user_id=data.get('user_id'),
                context=data.get('context')
            )
        except Exception as e:
            error_response = ErrorResponse(error=f"请求格式错误: {str(e)}", status_code=400)
            return jsonify(error_response.__dict__), 400

        # 验证必填字段
        if not chat_request.question:
            error_response = ErrorResponse(error="问题不能为空", status_code=400)
            return jsonify(error_response.__dict__), 400

        # 获取会话ID，如果没有则生成一个
        session_id = chat_request.session_id
        if not session_id:
            session_id = str(uuid.uuid4())
            logger.info(f"为新对话生成会话ID: {session_id}")

        # 处理聊天请求
        result = chat_service.process_message(
            question=chat_request.question,
            session_id=session_id,
            user_id=chat_request.user_id or 'anonymous',
            context=chat_request.context or {}
        )

        # 构建响应
        chat_response = ChatResponse(
            session_id=session_id,
            answer=result.get("content", ""),
            error=result.get("error", False),
            ragflow_session_id=result.get("ragflow_session_id")
        )

        return jsonify(chat_response.__dict__)

    except Exception as e:
        logger.error(f"处理聊天请求时发生错误: {e}", exc_info=True)
        error_response = ErrorResponse(error="服务器内部错误", status_code=500)
        return jsonify(error_response.__dict__), 500


@api_bp.route('/sessions/<session_id>', methods=['DELETE'])
def clear_session(session_id):
    """清除会话"""
    try:
        success = chat_service.clear_session(session_id)
        if success:
            status_response = StatusResponse(status="success", message="会话已清除")
            return jsonify(status_response.__dict__)
        else:
            error_response = ErrorResponse(error="会话不存在", status_code=404)
            return jsonify(error_response.__dict__), 404

    except Exception as e:
        logger.error(f"清除会话时发生错误: {e}", exc_info=True)
        error_response = ErrorResponse(error="服务器内部错误", status_code=500)
        return jsonify(error_response.__dict__), 500


@api_bp.route('/sessions', methods=['DELETE'])
def clear_all_sessions():
    """清除所有会话"""
    try:
        chat_service.clear_all_sessions()
        status_response = StatusResponse(status="success", message="所有会话已清除")
        return jsonify(status_response.__dict__)

    except Exception as e:
        logger.error(f"清除所有会话时发生错误: {e}", exc_info=True)
        error_response = ErrorResponse(error="服务器内部错误", status_code=500)
        return jsonify(error_response.__dict__), 500


@api_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    status_response = StatusResponse(status="healthy", message="ragflow-service")
    return jsonify(status_response.__dict__)


@api_bp.route('/receive', methods=['POST'])
def receive():
    """接收微信消息并处理"""
    try:
        data = request.get_json()
        logger.info(f"收到消息: {data}")

        if not data or 'event' not in data or data['event'] != 10010:
            logger.warning("无效的消息格式")
            return jsonify({"status": "error", "message": "无效的消息格式"}), 400

        msg_data = data.get('data', {}).get('data', {})
        if not msg_data:
            logger.warning("消息数据为空")
            return jsonify({"status": "error", "message": "消息数据为空"}), 400

        # 提取消息内容
        msg_content = msg_data.get('msg', '')
        if not msg_content:
            logger.warning("消息内容为空")
            return jsonify({"status": "ok"}), 200

        # 确定消息来源
        from_type = msg_data.get('fromType', 0)
        from_wxid = msg_data.get('fromWxid', '')
        final_from_wxid = msg_data.get('finalFromWxid', '')

        # 判断是群聊还是私聊
        is_group = from_type == 2

        # 处理特殊命令
        if msg_content == "#清除记忆":
            success = chat_service.clear_wechat_session(from_wxid)
            status = "success" if success else "failed"
            return jsonify({"status": status, "message": "会话已清除" if success else "会话不存在"})

        if msg_content == "#清除所有":
            chat_service.clear_all_wechat_sessions()
            return jsonify({"status": "success", "message": "所有会话已清除"})

        # 处理普通消息
        result = chat_service.process_wechat_message(
            question=msg_content,
            wxid=from_wxid,
            user_id=final_from_wxid or from_wxid,
            is_group=is_group,
            context={"is_group": is_group}
        )

        # 这里可以添加发送回复的逻辑
        # 例如调用微信API发送回复
        print(result)

        return jsonify({
            "status": "ok",
            "wxid": from_wxid,
            "ragflow_session_id": result.get("ragflow_session_id"),
            "answer": result.get("content"),
            "error": result.get("error", False)
        })

    except Exception as e:
        logger.error(f"处理微信消息时发生错误: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500
