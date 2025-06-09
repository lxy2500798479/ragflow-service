import logging
import redis  # 引入redis

from ragflow.client import RagFlowClient

# SessionManager 和 RagFlowSession 在此场景下可能不再直接用于微信会话管理，
# 因为我们将直接用 Redis 存储 wxid -> ragflow_session_id 的映射。
# 但如果通用 /api/chat 接口仍需使用它们，则保留。

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, api_key, api_base, default_chat_id, session_expiry, max_tokens, fallback_reply,
                 redis_config):  # 添加 redis_config
        """
        初始化聊天服务
        """
        self.ragflow_client = RagFlowClient(api_key, api_base, default_chat_id)
        self.default_chat_id = default_chat_id
        # self.session_manager = SessionManager(expiry_seconds=session_expiry) # 通用 session 管理器
        self.max_tokens = max_tokens
        self.fallback_reply = fallback_reply
        self.ragflow_session_expiry_redis = redis_config.get('RAGFLOW_SESSION_EXPIRY_REDIS', 3600)

        # 初始化 Redis 客户端
        try:
            self.redis_client = redis.StrictRedis(
                host=redis_config['REDIS_HOST'],
                port=redis_config['REDIS_PORT'],
                db=redis_config['REDIS_DB'],
                password=redis_config['REDIS_PASSWORD'],
                decode_responses=True  # 重要：这样get出来的值是字符串而不是bytes
            )
            self.redis_client.ping()  # 测试连接
            logger.info("成功连接到 Redis")
        except Exception as e:
            logger.error(f"连接 Redis 失败: {e}")
            self.redis_client = None

        # 不再使用 self.wxid_to_session 字典
        # self.wxid_to_session = {}

        logger.info("聊天服务已初始化 (微信会话使用 Redis)")

    def get_or_create_ragflow_session_for_wechat(self, session_key: str, title_prefix: str, is_group_user: bool):
        """
        从 Redis 获取或创建 RagFlow 会话ID，并存储到 Redis。
        session_key: 用于 Redis 存储的键 (如 finalFromWxid 或 fromWxid)
        title_prefix: 用于创建新会话时的标题前缀 (如 "群聊用户" 或 "私聊")
        is_group_user: 是否为群聊用户，用于生成标题
        """
        if not self.redis_client:
            logger.error("Redis 客户端未初始化，无法获取或创建会话")
            return None

        # 尝试从 Redis 获取已存在的 RagFlow 会话ID
        ragflow_session_id = self.redis_client.get(session_key)

        if ragflow_session_id:
            logger.info(f"从 Redis 找到现有会话: {session_key} -> {ragflow_session_id}")
            # 每次获取时刷新过期时间
            self.redis_client.expire(session_key, self.ragflow_session_expiry_redis)
            return ragflow_session_id
        else:
            # 创建新会话
            if is_group_user:
                title = f"{title_prefix} {session_key[:8]}"  # 使用 session_key (即 finalFromWxid)
            else:
                title = f"{title_prefix} {session_key[:8]}"  # 使用 session_key (即 fromWxid)

            new_ragflow_session_id = self.ragflow_client.create_session(
                chat_id=self.default_chat_id,
                title=title
            )

            if not new_ragflow_session_id:
                logger.error(f"创建 RagFlow 会话失败，Redis Key: {session_key}")
                return None

            # 保存到 Redis，并设置过期时间
            self.redis_client.setex(session_key, self.ragflow_session_expiry_redis, new_ragflow_session_id)
            logger.info(f"创建新 RagFlow 会话并存入 Redis: {session_key} -> {new_ragflow_session_id}")
            return new_ragflow_session_id

    def process_wechat_message(self, question, from_wxid, final_from_wxid, is_group, context=None):
        """
        处理微信消息 (修改版)
        from_wxid: 对于私聊是对方wxid，对于群聊是群wxid
        final_from_wxid: 群聊中消息发送者的wxid，私聊中为空
        is_group: 是否为群聊
        """
        if context is None:
            context = {}

            # 检查是否是机器人自己发送的消息
        bot_wxid = context.get('bot_wxid', '')
        # 私聊中，如果 finalFromWxid 是机器人自己的wxid，说明是机器人发送的消息
        if not is_group and final_from_wxid and final_from_wxid == bot_wxid:
            logger.info(f"私聊消息来自机器人自身，忽略。from_wxid: {from_wxid}, finalFromWxid: {final_from_wxid}")
            return {
                "content": "",
                "error": False,
                "ignore_self_message": True
            }

        session_key_for_redis = ""
        title_prefix_for_new_session = ""
        is_group_user_session = False  # 用于判断标题生成方式

        if is_group:
            session_key_for_redis = f"wx_session:group_user:{final_from_wxid}"  # 使用 finalFromWxid 作为群聊用户的key
            title_prefix_for_new_session = "群聊用户"
            is_group_user_session = True
        else:
            session_key_for_redis = f"wx_session:private:{from_wxid}"  # 使用 fromWxid 作为私聊的key
            title_prefix_for_new_session = "私聊"
            is_group_user_session = False

        logger.info(f"微信消息处理: session_key_for_redis='{session_key_for_redis}', is_group={is_group}")

        ragflow_session_id = self.get_or_create_ragflow_session_for_wechat(
            session_key_for_redis,
            title_prefix_for_new_session,
            is_group_user_session
        )

        if not ragflow_session_id:
            return {
                "content": "抱歉，创建或获取会话失败，请稍后再试。",
                "error": True
            }

        # 发送消息到RagFlow
        response = self.ragflow_client.send_message(
            question=question,
            session_id=ragflow_session_id,  # 使用从 Redis 获取或新创建的 RagFlow session ID
            chat_id=self.default_chat_id
        )

        if response.get("error"):
            logger.error(f"RagFlow 响应错误: {response.get('error_message')}")
            # 即使出错，也返回 ragflow_session_id，因为会话可能已经建立
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

    def clear_wechat_session(self, from_wxid, final_from_wxid, is_group):
        """
        清除指定微信会话 (基于 Redis)
        """
        if not self.redis_client:
            logger.error("Redis 客户端未初始化，无法清除会话")
            return False

        session_key_to_clear = ""
        if is_group:
            if not final_from_wxid:
                logger.warning(f"尝试清除群聊会话，但 final_from_wxid 为空，无法定位用户会话。群ID: {from_wxid}")
                return False
            session_key_to_clear = f"wx_session:group_user:{final_from_wxid}"
        else:
            session_key_to_clear = f"wx_session:private:{from_wxid}"

        if self.redis_client.exists(session_key_to_clear):
            self.redis_client.delete(session_key_to_clear)
            logger.info(f"已从 Redis 清除会话: {session_key_to_clear}")
            return True
        else:
            logger.info(f"尝试清除的会话在 Redis 中不存在: {session_key_to_clear}")
            return False

    def clear_all_wechat_sessions(self):
        """
        清除所有微信相关的会话 (从 Redis 中，基于 "wx_session:" 前缀)
        注意：这个操作可能比较耗时，取决于key的数量。
        """
        if not self.redis_client:
            logger.error("Redis 客户端未初始化，无法清除所有会话")
            return

        count = 0
        # 使用 scan_iter 迭代匹配的key，避免一次性加载过多key导致阻塞
        for key in self.redis_client.scan_iter("wx_session:*"):
            self.redis_client.delete(key)
            count += 1
        logger.info(f"已从 Redis 清除所有 {count} 个微信会话 (前缀 wx_session:*)")

    # --- 原有的通用 chat service 方法 ---
    # 如果 /api/chat 接口仍然需要基于 SessionManager 的会话，
    # 则 ChatService 中原有的 process_message, clear_session, clear_all_sessions 方法需要保留并适配。
    # 但根据您的提问，主要关注的是微信 /receive 接口的会话。
    # 以下是示例性的保留，如果您的 /api/chat 接口不再使用，可以移除或重构。
    # def process_message(self, question, session_id, user_id, context):
    #     """ 这是原来 /api/chat 接口调用的方法，如果它也需要改用Redis或保持原样，需明确 """
    #     # ... 原有逻辑或修改后的逻辑 ...
    #     logger.warning("通用 process_message 方法被调用，请确认其会话管理方式是否需要同步修改。")
    #     # 这是一个占位，您需要根据 /api/chat 的具体需求实现
    #     # 比如，它可能也需要一个 session_key_prefix (e.g., "generic_session:") 来存入 Redis
    #     # 或者继续使用 self.session_manager
    #     return {"content": "通用接口待处理", "error": True, "session_id": session_id}

    # def clear_session(self, session_id: str) -> bool:
    #    # 原 /api/sessions/{session_id} 调用的方法
    #    # return self.session_manager.clear_session(session_id)
    #    logger.warning("通用 clear_session 方法被调用，请确认其会话管理方式。")
    #    return False # 占位

    # def clear_all_sessions(self) -> None:
    #    # 原 /api/sessions 调用的方法
    #    # self.session_manager.clear_all_sessions()
    #    logger.warning("通用 clear_all_sessions 方法被调用，请确认其会话管理方式。")
    #    pass # 占位
