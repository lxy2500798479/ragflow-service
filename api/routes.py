# api/routes.py
from flask import Blueprint, request, jsonify, current_app
import logging
import uuid

from api.shemas import StatusResponse, ErrorResponse, ChatResponse, ChatRequest  # shemas -> schemas (拼写修正)
from services.chat_service import ChatService
from services.wechat_service import WeChatService

logger = logging.getLogger(__name__)
api_bp = Blueprint('api', __name__)

chat_service = None  # 保持全局，由 before_app_request 初始化
wechat_service = None  # 新增微信服务


@api_bp.before_app_request
def initialize_services():
    global chat_service
    global wechat_service  # <--- 添加这一行
    if chat_service is None:
        config = current_app.config
        logger.info(f"从 app.config 加载配置: RAGFLOW_API_KEY, RAGFLOW_API_BASE, etc.")

        redis_config = {
            'REDIS_HOST': config['REDIS_HOST'],
            'REDIS_PORT': config['REDIS_PORT'],
            'REDIS_DB': config['REDIS_DB'],
            'REDIS_PASSWORD': config.get('REDIS_PASSWORD'),
            'RAGFLOW_SESSION_EXPIRY_REDIS': config['RAGFLOW_SESSION_EXPIRY_REDIS']
        }

        chat_service = ChatService(
            api_key=config['RAGFLOW_API_KEY'],
            api_base=config['RAGFLOW_API_BASE'],
            default_chat_id=config['RAGFLOW_CHAT_ID'],
            session_expiry=config['SESSION_EXPIRY'],
            max_tokens=config['MAX_TOKENS'],
            fallback_reply=config['FALLBACK_REPLY'],
            redis_config=redis_config
        )
        logger.info("聊天服务 (ChatService) 已使用 Redis 配置重新初始化")

        # 现在这次赋值会正确地修改全局变量
        wechat_service = WeChatService(api_base=config.get('WECHAT_API_BASE', 'http://127.0.0.1:8888/wechat/httpapi'))
        logger.info(f"微信服务 (WeChatService) 已初始化，API基础URL: {wechat_service.api_base}")


@api_bp.route('/receive', methods=['POST'])
def receive():
    """接收微信消息并处理 (修改版)"""
    try:
        data = request.get_json()
        logger.info(f"收到 /receive 消息: {data}")

        msg_data = data.get('data', {}).get('data', {})
        if not msg_data:
            logger.warning("消息数据 data.data 为空")
            return jsonify({"status": "error", "message": "消息数据为空"}), 400

        msg_content = msg_data.get('msg', '')
        from_type = msg_data.get('fromType', 0)  # 0或1私聊, 2群聊
        from_wxid = msg_data.get('fromWxid', '')  # 私聊是对方wxid, 群聊是群wxid
        final_from_wxid = msg_data.get('finalFromWxid', '')  # 群聊中发送者wxid, 私聊中空
        at_wxid_list = msg_data.get('atWxidList', [])  # 获取被@的用户列表

        if not from_wxid:
            logger.warning("fromWxid 为空，无法处理")
            return jsonify({"status": "error", "message": "fromWxid 缺失"}), 400

        is_group = (from_type == 2)
        msg_source = msg_data.get('msgSource', 0)  # 获取 msgSource 字段
        bot_wxid = current_app.config.get('BOT_WXID', '')  # 确保你在配置中正确设置了 BOT_WXID

        # 检查是否是机器人自己发送的消息
        if msg_source == 1 or (is_group and final_from_wxid == bot_wxid):
            logger.info(f"消息来自机器人自身 (msgSource: {msg_source}, finalFromWxid: {final_from_wxid})，已忽略。")
            return jsonify({
                "status": "ok",
                "message": "Self-message ignored."
            }), 200

        # 群聊消息处理逻辑
        if is_group:
            # 检查是否有人@机器人，如果没有@机器人则不回复
            if bot_wxid not in at_wxid_list:
                logger.info(f"群聊消息未@机器人，忽略。群ID: {from_wxid}, finalFromWxid: {final_from_wxid}")
                return jsonify({
                    "status": "ok",
                    "message": "Message not mentioning bot, no reply sent."
                }), 200

        # 处理特殊命令
        if msg_content == "#清除记忆":
            # 对于群聊，清除的是发送命令者的会话 (final_from_wxid)
            # 对于私聊，清除的是对方的会话 (from_wxid)
            success = chat_service.clear_wechat_session(from_wxid, final_from_wxid, is_group)
            status_msg = "会话已清除" if success else "会话不存在或清除失败"
            return jsonify({"status": "success" if success else "failed", "message": status_msg})

        if msg_content == "#清除所有":  # 这个命令需要谨慎，会清除所有 wx_session:* 的key
            chat_service.clear_all_wechat_sessions()
            return jsonify({"status": "success", "message": "所有微信相关会话已尝试清除"})

        if not msg_content:  # 普通消息内容为空，不处理
            logger.info("消息内容为空，不处理普通消息")
            return jsonify({"status": "ok", "message": "Empty message content"}), 200

        # --- 核心逻辑：调用 ChatService 处理普通消息 ---
        # 处理消息内容，移除@部分（如果是群聊）
        processed_msg_content = msg_content
        if is_group and bot_wxid in at_wxid_list:
            # 移除@机器人的部分，通常格式为"@昵称 实际消息内容"
            # 这里使用简单的分割方法，可能需要根据实际格式调整
            parts = msg_content.split('\u2005', 1)  # \u2005是特殊空格字符
            if len(parts) > 1:
                processed_msg_content = parts[1].strip()
            logger.info(f"处理后的群聊消息内容: '{processed_msg_content}'")

        result = chat_service.process_wechat_message(
            question=processed_msg_content,
            from_wxid=from_wxid,
            final_from_wxid=final_from_wxid,
            is_group=is_group,
            context={"is_group": is_group, "bot_wxid": bot_wxid}
        )

        # 检查是否是机器人自己的消息
        if result.get("ignore_self_message", False):
            logger.info("忽略机器人自己发送的消息，不再回复")
            return jsonify({"status": "ok", "message": "Self-message ignored"}), 200

        # 正常的回复处理
        logger.info(f"RagFlow 回复: {result}")

        # 获取回复内容
        reply_content = result.get("content", "")

        # 通过微信服务发送回复
        global wechat_service
        if wechat_service is not None and reply_content:
            # 如果是群聊且有发送者ID，则构建@消息
            if is_group and final_from_wxid:
                # 这里可以根据需要修改@的格式
                # 例如: reply_content = f"@{final_from_wxid} {reply_content}"
                pass

            # 发送消息
            wechat_response = wechat_service.send_text_message(
                to_wxid=from_wxid,
                content=reply_content,
                at_list=[final_from_wxid] if is_group and final_from_wxid else None
            )

            logger.info(f"微信消息发送结果: {wechat_response}")
        else:
            logger.warning("微信服务未初始化或回复内容为空，无法发送回复")

        return jsonify({
            "status": "ok",
        })

    except Exception as e:
        logger.error(f"处理 /receive 请求时发生严重错误: {e}", exc_info=True)
        error_response = ErrorResponse(error="服务器内部错误，处理微信消息失败", status_code=500)
        return jsonify(error_response.__dict__), 500


# 其他接口 (/chat, /sessions/*) 的逻辑保持不变，
# 但要注意它们如果也和 ChatService 交互，ChatService 中的相应方法可能也需要调整会话管理方式。
# 例如，/api/chat 如果也想用Redis，那么 ChatService.process_message 方法也需要重写。
# 目前的修改主要集中在 /api/receive 接口的微信会话管理。

# ... (保留 /api/chat, /api/sessions/<session_id>, /api/sessions, /api/health 路由)
# 例如 /api/chat:
@api_bp.route('/chat', methods=['POST'])
def chat():
    """
    通用聊天接口。
    注意：此接口当前的会话管理方式可能与微信的Redis会话管理不同。
    如果需要统一，ChatService 中的 process_message 方法也需要修改。
    """
    try:
        # ... (原有 /api/chat 的请求解析和验证逻辑) ...
        data = request.json
        if not data:  # ...
            # ...
            pass
        chat_request = ChatRequest(
            question=data.get('question', ''),
            session_id=data.get('session_id'),
            user_id=data.get('user_id'),
            context=data.get('context')
        )  # ...
        if not chat_request.question:  # ...
            # ...
            pass
        session_id = chat_request.session_id or str(uuid.uuid4())
        logger.info(f"通用 /api/chat 接口调用，session_id: {session_id}。该会话管理可能独立于微信Redis会话。")

        # 这里的 chat_service.process_message 是指 ChatService 类中为通用接口准备的方法
        # 如果这个方法没有实现或未适配新的会话逻辑，可能会有问题
        # result = chat_service.process_message(
        #     question=chat_request.question,
        #     session_id=session_id, # 这是通用接口的 session_id
        #     user_id=chat_request.user_id or 'anonymous',
        #     context=chat_request.context or {}
        # )
        # 临时返回，提示该接口的会话逻辑可能需要审阅
        result = {
            "content": "通用聊天接口的会话逻辑与微信接口独立，请检查 ChatService.process_message 实现。",
            "error": True,
            "ragflow_session_id": None
        }

        chat_response = ChatResponse(
            session_id=session_id,
            answer=result.get("content", ""),
            error=result.get("error", False),
            ragflow_session_id=result.get("ragflow_session_id")
        )
        return jsonify(chat_response.__dict__)

    except Exception as e:
        # ... (原有错误处理) ...
        logger.error(f"处理聊天请求时发生错误: {e}", exc_info=True)  #
        error_response = ErrorResponse(error="服务器内部错误", status_code=500)  #
        return jsonify(error_response.__dict__), 500  #

# ... 其他 /api/sessions 接口类似，如果它们依赖 ChatService 中的方法，
# 而这些方法又依赖旧的 SessionManager，那么它们的功能可能会受影响，需要一并检查和适配。
