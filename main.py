from astrbot.api.event import AstrMessageEvent
from astrbot.api.event import filter
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.all import *
import astrbot.api.message_components as Comp

# 尝试导入command装饰器
try:
    from astrbot.api.star import command
except ImportError:
    try:
        from astrbot.api.all import command
    except ImportError:
        # 如果无法导入，定义一个简单的替代
        def command(cmd_name):
            def decorator(func):
                func._command_name = cmd_name
                return func
            return decorator
from typing import Dict, List, Optional
from collections import defaultdict, deque
import asyncio
import concurrent.futures
import schedule
import threading
import time
from datetime import datetime

# 导入数据存储模块
from .data_storage import DataStorage


@register(
    "astrbot_plugin_dzmm",
    "VincenttHo",
    "DZMM AI聊天插件，可以与dzmm平台的ai进行各种深度聊天",
    "1.1.1",
    "https://github.com/VincenttHo/astrbot_plugin_dzmm",
)
class PluginDzmm(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config

        # 基础配置参数
        self.context_length = self.config.get("context_length", 10)
        self.api_url = self.config.get("api_url", "https://www.gpt4novel.com/api/xiaoshuoai/ext/v1/chat/completions")
        self.model = self.config.get("model", "nalang-turbo-v23")
        self.temperature = self.config.get("temperature", 0.7)
        self.max_tokens = self.config.get("max_tokens", 800)
        self.top_p = self.config.get("top_p", 0.35)
        self.repetition_penalty = self.config.get("repetition_penalty", 1.05)

        # 新增配置选项
        self.show_nickname = self.config.get("show_nickname", True)
        self.group_shared_context = self.config.get("group_shared_context", True)
        self.enable_memory = self.config.get("enable_memory", True)
        self.reply_to_at = self.config.get("reply_to_at", False)
        
        # 定时触发配置
        self.enable_auto_trigger = self.config.get("enable_auto_trigger", False)
        self.auto_trigger_interval = max(1, min(10080, self.config.get("auto_trigger_interval", 1440)))  # 限制在1-10080分钟之间（1小时-7天）
        self.auto_trigger_message = self.config.get("auto_trigger_message", "（注：由于我很久没跟你说话，你开始寂寞，你主动找我...）")
        self.auto_trigger_whitelist = self._parse_list_config("auto_trigger_whitelist", [])
        
        # 用户最后活动时间记录
        self.user_last_activity = {}

        # 多角色配置
        self.personas = self._parse_json_config("personas", {
            "default": "你是一个有帮助的AI助手。",
            "programmer": "你是一个专业的程序员，擅长解决编程问题和代码优化。",
            "teacher": "你是一个耐心的老师，善于用简单易懂的方式解释复杂概念。",
            "translator": "你是一个专业的翻译，能够准确翻译各种语言。"
        })

        # 兼容旧版本的system_prompt配置
        old_system_prompt = self.config.get("system_prompt")
        if old_system_prompt and "default" not in self.personas:
            self.personas["default"] = old_system_prompt

        # 多API密钥配置
        self.api_keys = self._parse_json_config("api_keys", {})

        # 兼容旧版本的api_key配置
        old_api_key = self.config.get("api_key", "")
        if old_api_key and "default" not in self.api_keys:
            self.api_keys["default"] = old_api_key

        # 根据配置决定是否启用记忆功能
        if self.enable_memory:
            # 初始化数据存储
            self.data_storage = DataStorage("astrbot_plugin_dzmm")
            
            # 从存储中恢复数据
            if self.data_storage:
                self.user_contexts = self.data_storage.get_user_contexts(self.context_length)
                self.user_current_persona = self.data_storage.get_user_current_persona()
                self.user_current_api_key = self.data_storage.get_user_current_api_key()
                self.api_key_failures = self.data_storage.get_api_key_failures()
                
                # 恢复用户最后活动时间
                try:
                    self.user_last_activity = self.data_storage.get_user_last_activity()
                except:
                    self.user_last_activity = {}
            else:
                # 如果data_storage初始化失败，使用默认值
                self.user_contexts = defaultdict(lambda: deque(maxlen=self.context_length))
                self.user_current_persona = defaultdict(lambda: "default")
                self.user_current_api_key = defaultdict(lambda: "default")
                self.api_key_failures = defaultdict(int)
                self.user_last_activity = {}
            
            logger.info("DZMM插件: 记忆功能已启用，数据将自动保存和恢复")
        else:
            # 不启用记忆功能，使用默认初始化
            self.data_storage = None
            self.user_contexts = defaultdict(lambda: deque(maxlen=self.context_length))
            self.user_current_persona = defaultdict(lambda: "default")
            self.user_current_api_key = defaultdict(lambda: "default")
            self.api_key_failures = defaultdict(int)
            
            logger.info("DZMM插件: 记忆功能已禁用，数据不会保存")
        
        self.max_failures_before_switch = max(1, min(10, self.config.get("max_failures_before_switch", 3)))  # 连续失败多少次后切换key，限制在1-10之间
        
        # 初始化定时任务
        self._init_scheduler()
        
        # 启动定时触发任务（如果启用）
        self.auto_trigger_task = None
        if self.enable_auto_trigger:
            self.auto_trigger_task = asyncio.create_task(self._auto_trigger_task())
            logger.info(f"DZMM插件: 定时触发功能已启用，间隔时间: {self.auto_trigger_interval}分钟")

        # 验证API密钥
        if not self.api_keys or not any(self.api_keys.values()):
            logger.warning("DZMM插件: 未配置API密钥，插件将无法正常工作")

        # 调试信息：输出解析后的配置和恢复的数据
        logger.info(f"DZMM插件: 已加载 {len(self.personas)} 个角色: {list(self.personas.keys())}")
        logger.info(f"DZMM插件: 已加载 {len(self.api_keys)} 个API密钥: {list(self.api_keys.keys())}")
        
        # 输出恢复的数据统计
        if self.enable_memory and self.data_storage:
            stats = self.data_storage.get_storage_stats()
            logger.info(f"DZMM插件: 已恢复 {stats['total_users']} 个用户的上下文，共 {stats['total_messages']} 条消息")
            if stats['failed_keys'] > 0:
                logger.info(f"DZMM插件: 恢复了 {stats['failed_keys']} 个失败的API密钥计数")
        
        # 初始化白名单用户的最后活动时间
        self._init_whitelist_activity()

    def _parse_json_config(self, key: str, default_value: dict) -> dict:
        """解析JSON格式的配置项"""
        import json

        config_value = self.config.get(key)
        if not config_value:
            return default_value

        # 如果已经是字典类型，直接返回（向后兼容）
        if isinstance(config_value, dict):
            return config_value

        # 如果是字符串，尝试解析JSON
        if isinstance(config_value, str):
            try:
                parsed = json.loads(config_value)
                if isinstance(parsed, dict):
                    return parsed
                else:
                    logger.warning(f"DZMM插件: 配置项 {key} 不是有效的JSON对象，使用默认值")
                    return default_value
            except json.JSONDecodeError as e:
                logger.warning(f"DZMM插件: 配置项 {key} JSON解析失败: {str(e)}，使用默认值")
                return default_value

        logger.warning(f"DZMM插件: 配置项 {key} 格式不正确，使用默认值")
        return default_value

    def _parse_list_config(self, key: str, default_value: list) -> list:
        """解析列表格式的配置项，支持直接的list类型和JSON字符串格式"""
        import json

        config_value = self.config.get(key)
        if not config_value:
            return default_value

        # 如果已经是列表类型，直接返回（astrbot原生支持）
        if isinstance(config_value, list):
            return config_value

        # 如果是字符串，尝试解析JSON
        if isinstance(config_value, str):
            try:
                parsed = json.loads(config_value)
                if isinstance(parsed, list):
                    return parsed
                else:
                    logger.warning(f"DZMM插件: 配置项 {key} 不是有效的JSON数组，使用默认值")
                    return default_value
            except json.JSONDecodeError as e:
                logger.warning(f"DZMM插件: 配置项 {key} JSON解析失败: {str(e)}，使用默认值")
                return default_value

        logger.warning(f"DZMM插件: 配置项 {key} 格式不正确，使用默认值")
        return default_value

    def _init_whitelist_activity(self):
        """初始化白名单用户的最后活动时间"""
        if not self.enable_auto_trigger or not self.auto_trigger_whitelist:
            return
        
        current_time = datetime.now().timestamp()
        updated_count = 0
        
        for whitelist_entry in self.auto_trigger_whitelist:
            whitelist_entry = "aiocqhttp_private_" + whitelist_entry
            if whitelist_entry not in self.user_last_activity:
                self.user_last_activity[whitelist_entry] = current_time
                updated_count += 1
                logger.info(f"DZMM插件: 为白名单用户 {whitelist_entry} 初始化最后活动时间")
        
        if updated_count > 0:
            logger.info(f"DZMM插件: 已为 {updated_count} 个白名单用户初始化最后活动时间")
            
            # 持久化保存
            if self.enable_memory and self.data_storage:
                try:
                    self.data_storage.save_user_last_activity(self.user_last_activity)
                    logger.info("DZMM插件: 白名单用户活动时间已保存到存储")
                except Exception as e:
                    logger.error(f"DZMM插件: 保存白名单用户活动时间失败: {str(e)}")
        else:
            logger.info("DZMM插件: 所有白名单用户的最后活动时间已存在，无需初始化")

    def get_user_key(self, event: AstrMessageEvent) -> str:
        """生成用户唯一标识

        根据配置决定群聊是否共享上下文：
        - 群聊且启用共享：使用群组ID作为标识，所有群成员共享上下文
        - 群聊但禁用共享：使用用户ID作为标识，每个用户独立上下文
        - 私聊：使用用户ID作为标识，每个用户独立上下文
        """
        group_id = event.get_group_id()
        platform = event.get_platform_name() or "unknown"
        user_id = event.get_sender_id() or "unknown"

        if group_id and group_id != "private" and self.group_shared_context:
            # 群聊且启用共享上下文：所有成员共享上下文
            return f"{platform}_group_{group_id}"
        else:
            # 私聊或群聊但禁用共享：用户独立上下文
            return f"{platform}_private_{user_id}"

    def get_user_nickname(self, event: AstrMessageEvent) -> str:
        """获取用户昵称"""
        # 使用astrbot官方API获取用户昵称
        try:
            nickname = event.get_sender_name()
            if nickname:
                return nickname
        except Exception as e:
            logger.warning(f"DZMM插件: 获取用户昵称失败: {str(e)}")

        # 如果获取昵称失败，使用用户ID作为备选
        try:
            sender_id = event.get_sender_id()
            if sender_id:
                return f"用户{sender_id}"
        except Exception as e:
            logger.warning(f"DZMM插件: 获取用户ID失败: {str(e)}")

        return "匿名用户"

    def add_to_context(self, user_key: str, role: str, content: str, nickname: str = None):
        """添加消息到用户上下文"""
        if role == "user" and nickname and self.show_nickname:
            # 判断是否为群聊模式
            is_group_chat = "_group_" in user_key
            if is_group_chat:
                # 群聊模式：添加昵称信息
                formatted_content = f"[{nickname}]: {content}"
            else:
                # 私聊模式：不添加昵称
                formatted_content = content
        else:
            formatted_content = content

        self.user_contexts[user_key].append({"role": role, "content": formatted_content})
        
        # 更新用户最后活动时间（仅当是用户消息时）
        if role == "user":
            self.user_last_activity[user_key] = datetime.now().timestamp()
        
        # 保存用户上下文到存储（如果启用记忆功能）
        if self.enable_memory and self.data_storage:
            self.data_storage.save_user_contexts(self.user_contexts)
            # 保存用户最后活动时间
            if role == "user":
                self.data_storage.save_user_last_activity(self.user_last_activity)

    def get_context_messages(self, user_key: str) -> List[dict]:
        """获取用户的上下文消息"""
        # 获取用户当前使用的角色
        current_persona = self.user_current_persona[user_key]
        base_prompt = self.personas.get(current_persona, self.personas.get("default", "你是一个有帮助的AI助手。"))

        # 判断是否为群聊
        is_group_chat = "_group_" in user_key

        if is_group_chat:
            # 群聊模式：添加群聊相关的指导
            system_prompt = f"{base_prompt}\n\n（注意：关于聊天场景设定，这是一个群聊环境，可能会存在多个用户与你进行互动，你称呼用户时需要通过昵称区分，用户消息会以 `[昵称]: 消息内容` 的格式显示。请根据不同用户的昵称来区分发言者，并可以在回复中提及具体的用户昵称。）"
        else:
            # 私聊模式：使用原始提示词
            system_prompt = base_prompt

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(list(self.user_contexts[user_key]))
        return messages

    def get_current_api_key(self, user_key: str) -> str:
        """获取用户当前使用的API密钥"""
        current_key_name = self.user_current_api_key[user_key]
        return self.api_keys.get(current_key_name, self.api_keys.get("default", ""))
    
    def get_next_available_key(self, user_key: str) -> Optional[str]:
        """获取下一个可用的API密钥"""
        current_key_name = self.user_current_api_key[user_key]
        key_names = list(self.api_keys.keys())
        
        if not key_names:
            return None
            
        # 找到当前key在列表中的位置
        try:
            current_index = key_names.index(current_key_name)
        except ValueError:
            current_index = -1
            
        # 从下一个key开始尝试，如果到末尾则从头开始
        for i in range(len(key_names)):
            next_index = (current_index + 1 + i) % len(key_names)
            next_key_name = key_names[next_index]
            
            # 如果这个key的失败次数少于阈值，就使用它
            if self.api_key_failures[next_key_name] < self.max_failures_before_switch:
                return next_key_name
                
        # 如果所有key都失败了，重置失败计数并返回第一个key
        logger.warning("DZMM插件: 所有API密钥都已达到失败阈值，重置失败计数")
        self.api_key_failures.clear()
        return key_names[0] if key_names else None
    
    def switch_to_next_key(self, user_key: str) -> bool:
        """切换到下一个可用的API密钥"""
        next_key = self.get_next_available_key(user_key)
        if next_key and next_key != self.user_current_api_key[user_key]:
            old_key = self.user_current_api_key[user_key]
            self.user_current_api_key[user_key] = next_key
            logger.info(f"DZMM插件: 自动切换API密钥 {old_key} -> {next_key}")
            
            # 保存用户当前API密钥到存储（如果启用记忆功能）
            if self.enable_memory and self.data_storage:
                self.data_storage.save_user_current_api_key(self.user_current_api_key)
            return True
        return False
    
    def _init_scheduler(self):
        """初始化定时任务"""
        # 设置每天凌晨1点重置失败计数
        schedule.every().day.at("01:00").do(self._reset_all_key_failures)
        
        # 启动定时任务线程
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        logger.info("定时任务已启动，将在每天凌晨1点重置API密钥失败计数")
    
    def _reset_all_key_failures(self):
        """重置所有API密钥的失败计数"""
        self.api_key_failures.clear()
        if self.enable_memory and self.data_storage:
            self.data_storage.clear_api_key_failures()
        logger.info(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 已重置所有API密钥的失败计数")
    
    async def _auto_trigger_task(self):
        """定时触发任务"""
        while True:
            try:
                await self._execute_auto_trigger(False)
            except Exception as e:
                logger.error(f"DZMM插件: 定时触发任务发生错误: {str(e)}")
                await asyncio.sleep(300)  # 出错时等待5分钟再继续
    
    async def _execute_auto_trigger(self, is_test):
        """执行定时触发"""
        trigger_threshold = self.auto_trigger_interval * 60  # 转换为秒（分钟*60）

        if not is_test:
            await asyncio.sleep(trigger_threshold - 10)
        
        if not self.enable_auto_trigger:
            return
        
        current_time = datetime.now().timestamp()
        
        # 检查每个用户的最后活动时间
        for user_key, last_activity in list(self.user_last_activity.items()):
            # 只处理私聊用户
            if "_private_" not in user_key:
                continue
            
            # 提取用户ID进行白名单检查
            user_id = user_key.split("_private_")[-1]
            if not self.auto_trigger_whitelist or user_id not in self.auto_trigger_whitelist:
                continue
            
            # 检查是否超过触发间隔
            if current_time - last_activity >= trigger_threshold:
                await self._send_auto_trigger_message(user_key)
                # 更新最后活动时间，避免重复触发
                self.user_last_activity[user_key] = current_time
                if self.enable_memory and self.data_storage:
                    self.data_storage.save_user_last_activity(self.user_last_activity)
                
    async def _send_auto_trigger_message(self, user_key: str):
        """发送定时触发消息"""
        try:
            # 构造unified_msg_origin
            platform, chat_type, user_id = user_key.split("_", 2)
            # 根据AstrBot框架的MessageType，private应该是FriendMessage
            if chat_type == "private":
                message_type = "FriendMessage"
            elif chat_type == "group":
                message_type = "GroupMessage"
            else:
                message_type = chat_type  # 保持原值作为fallback
            unified_msg_origin = f"{platform}:{message_type}:{user_id}"
            
            # 添加触发消息到上下文
            self.add_to_context(user_key, "user", self.auto_trigger_message)
            
            # 获取完整的消息列表
            messages = self.get_context_messages(user_key)
            
            # 调用AI接口
            ai_response = await self.chat_with_ai(messages, user_key)
            
            if ai_response:
                # 添加AI回复到上下文
                self.add_to_context(user_key, "assistant", ai_response)
                
                # 发送消息
                from astrbot.api.event import MessageChain
                message_chain = MessageChain().message(ai_response)
                await self.context.send_message(unified_msg_origin, message_chain)
                
                logger.info(f"DZMM插件: 成功发送定时触发回复给用户 {user_key}")
            else:
                logger.warning(f"DZMM插件: 定时触发时AI无法回复，用户: {user_key}")
                
        except Exception as e:
            logger.error(f"DZMM插件: 发送定时触发消息时发生错误: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

    def _sync_chat_with_ai(self, messages: List[dict], api_key: str) -> tuple[Optional[str], bool]:
        """同步版本的AI聊天函数，支持完整的消息历史
        
        Returns:
            tuple: (response_content, is_key_error)
            - response_content: AI的回复内容，失败时为None
            - is_key_error: 是否是API密钥相关的错误（如使用次数超限）
        """
        import requests
        import json

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        request_body = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "repetition_penalty": self.repetition_penalty
        }

        all_content_parts = []

        try:
            with requests.post(self.api_url, headers=headers, json=request_body, stream=True) as response:
                # 检查HTTP状态码
                if response.status_code == 401:
                    logger.warning(f"DZMM插件: API密钥认证失败 (401)")
                    return None, True
                elif response.status_code == 429:
                    logger.warning(f"DZMM插件: API使用次数超限 (429)")
                    return None, True
                elif response.status_code == 403:
                    logger.warning(f"DZMM插件: API访问被拒绝 (403)")
                    return None, True
                
                response.raise_for_status()

                for line_bytes in response.iter_lines():
                    if line_bytes:
                        decoded_line = line_bytes.decode('utf-8')

                        if decoded_line.startswith('data: '):
                            json_data_str = decoded_line[len('data: '):].strip()

                            if not json_data_str:
                                continue

                            if json_data_str == "[DONE]":
                                break

                            try:
                                json_data = json.loads(json_data_str)
                                
                                # 检查是否有错误信息
                                if "error" in json_data:
                                    error_info = json_data["error"]
                                    error_code = error_info.get("code", "")
                                    error_message = error_info.get("message", "")
                                    
                                    # 检查是否是密钥相关错误
                                    if any(keyword in error_message.lower() for keyword in 
                                          ["quota", "limit", "exceeded", "insufficient", "balance", "credit"]):
                                        logger.warning(f"DZMM插件: API密钥使用限制错误: {error_message}")
                                        return None, True
                                    elif "invalid" in error_message.lower() and "key" in error_message.lower():
                                        logger.warning(f"DZMM插件: API密钥无效错误: {error_message}")
                                        return None, True
                                    else:
                                        logger.error(f"DZMM插件: API返回错误: {error_message}")
                                        return None, True

                                if json_data.get("completed"):
                                    break

                                choices = json_data.get("choices")
                                if choices and len(choices) > 0:
                                    delta = choices[0].get("delta")
                                    if delta and delta.get("content"):
                                        content_piece = delta["content"]
                                        all_content_parts.append(content_piece)

                            except json.JSONDecodeError:
                                if json_data_str.strip():
                                    logger.warning(f"DZMM插件: 解析JSON时出错: '{json_data_str}'")

            if all_content_parts:
                return "".join(all_content_parts), False
            else:
                return None, False

        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            # 检查是否是密钥相关的网络错误
            if any(keyword in error_msg.lower() for keyword in ["401", "403", "429", "unauthorized", "forbidden"]):
                logger.error(f"DZMM插件: API密钥相关的请求错误: {error_msg}")
                return None, True
            else:
                logger.error(f"DZMM插件: 网络请求错误: {error_msg}")
                return None, False
        except Exception as e:
            logger.error(f"DZMM插件: 发生未知错误: {str(e)}")
            return None, False

    async def chat_with_ai(self, messages: List[dict], user_key: str) -> Optional[str]:
        """调用AI接口进行聊天，支持自动key切换"""
        if not self.api_keys or not any(self.api_keys.values()):
            return "错误：未配置API密钥，请联系管理员配置插件"

        max_retries = len(self.api_keys)  # 最多重试次数等于key的数量
        current_retry = 0
        
        while current_retry < max_retries:
            current_key_name = self.user_current_api_key[user_key]
            api_key = self.get_current_api_key(user_key)
            
            if not api_key:
                logger.error(f"DZMM插件: 当前API密钥 '{current_key_name}' 为空")
                # 尝试切换到下一个key
                if not self.switch_to_next_key(user_key):
                    return "错误：所有API密钥都无效，请联系管理员检查配置"
                current_retry += 1
                continue

            try:
                # 在线程池中运行同步函数
                loop = asyncio.get_event_loop()
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    result, is_key_error = await loop.run_in_executor(
                        executor,
                        lambda: self._sync_chat_with_ai(messages, api_key)
                    )

                if result:
                    # 成功获得回复，重置当前key的失败计数
                    self.api_key_failures[current_key_name] = 0
                    if self.enable_memory and self.data_storage:
                        self.data_storage.save_api_key_failures(self.api_key_failures)
                    return result
                elif is_key_error:
                    # 是密钥相关错误，增加失败计数并尝试切换key
                    self.api_key_failures[current_key_name] += 1
                    if self.enable_memory and self.data_storage:
                        self.data_storage.save_api_key_failures(self.api_key_failures)
                    logger.warning(f"DZMM插件: API密钥 '{current_key_name}' 失败次数: {self.api_key_failures[current_key_name]}")
                    
                    # 如果失败次数达到阈值，尝试切换key
                    if self.api_key_failures[current_key_name] >= self.max_failures_before_switch:
                        if self.switch_to_next_key(user_key):
                            logger.info(f"DZMM插件: 因连续失败已自动切换API密钥")
                        else:
                            logger.warning(f"DZMM插件: 无法切换到其他API密钥")
                    
                    current_retry += 1
                    continue
                else:
                    # 非密钥错误，直接返回失败
                    return "抱歉，AI服务暂时不可用，请稍后再试"

            except Exception as e:
                logger.error(f"DZMM插件: 调用AI接口时发生错误: {str(e)}")
                # 对于未知错误，也尝试切换key
                self.api_key_failures[current_key_name] += 1
                if self.enable_memory and self.data_storage:
                    self.data_storage.save_api_key_failures(self.api_key_failures)
                if self.api_key_failures[current_key_name] >= self.max_failures_before_switch:
                    self.switch_to_next_key(user_key)
                current_retry += 1
                continue
        
        # 所有重试都失败了
        return "抱歉，所有API密钥都暂时不可用，请稍后再试或联系管理员"

    @command("dzmm")
    async def dzmm_chat(self, event: AstrMessageEvent, content: str = None):
        """AI聊天命令"""
        if not content or not content.strip():
            yield event.plain_result(
                "使用方法：\n"
                "/dzmm [内容] - 与AI聊天\n"
                "/dzmm help - 显示帮助信息\n"
                "\n管理命令：\n"
                "/dzmm_personas - 列出所有角色\n"
                "/dzmm_persona [角色名] - 切换角色\n"
                "/dzmm_keyls - 列出所有API密钥及状态\n"
                "/dzmm_key [密钥名] - 切换API密钥\n"
                "/dzmm_resetkeys - 重置API密钥失败计数\n"
                "/dzmm_status - 显示当前状态\n"
                "/dzmm_clear - 清除聊天上下文"
            )
            return

        content = content.strip()
        user_key = self.get_user_key(event)

        # 调试信息：记录收到的命令
        logger.info(f"DZMM插件: 收到命令 '{content}'")

        # 处理特殊命令
        if content.lower() == "help":
            trigger_help = ""
            if self.enable_auto_trigger:
                trigger_help = (
                    "\n⏰ 定时触发功能：\n"
                    "• /dzmm_trigger_status - 查看定时触发状态\n"
                    "• /dzmm_trigger_test - 测试定时触发功能\n"
                    f"• 触发间隔：{self.auto_trigger_interval}小时\n"
                    "• 仅对私聊白名单用户有效\n"
                )
            
            yield event.plain_result(
                "DZMM AI聊天插件帮助：\n"
                "\n基础命令：\n"
                "• /dzmm [内容] - 与AI聊天，支持上下文对话\n"
                "• /dzmm help - 显示此帮助信息\n"
                "\n管理命令：\n"
                "• /dzmm_personas - 列出所有可用角色\n"
                "• /dzmm_persona [角色名] - 切换到指定角色\n"
                "• /dzmm_keyls - 列出所有API密钥及状态\n"
                "• /dzmm_key [密钥名] - 切换到指定API密钥\n"
                "• /dzmm_resetkeys - 重置API密钥失败计数\n"
                "• /dzmm_status - 显示当前状态\n"
                "• /dzmm_clear - 清除聊天上下文\n"
                f"{trigger_help}\n"
                "🔄 自动切换功能：\n"
                f"• 当API密钥连续失败{self.max_failures_before_switch}次时自动切换\n"
                "• 切换过程对用户透明，无需手动干预\n"
                "• 使用 /dzmm_keyls 查看密钥状态\n"
                "• 每天凌晨1点自动重置失败计数\n\n"
                f"当前配置：\n"
                f"• 上下文长度：{self.context_length}条消息\n"
                f"• 模型：{self.model}\n"
                f"• 温度：{self.temperature}"
            )
            return

        if content.lower() == "clear":
            self.user_contexts[user_key].clear()
            yield event.plain_result("✅ 已清除聊天上下文")
            return

        # 普通聊天处理
        # 获取用户昵称
        nickname = self.get_user_nickname(event)

        # 添加用户消息到上下文（包含昵称信息）
        self.add_to_context(user_key, "user", content, nickname)

        # 获取完整的消息列表
        messages = self.get_context_messages(user_key)

        # 调用AI接口
        try:
            ai_response = await self.chat_with_ai(messages, user_key)

            if ai_response:
                # 添加AI回复到上下文
                self.add_to_context(user_key, "assistant", ai_response)
                yield event.plain_result(ai_response)
            else:
                yield event.plain_result("抱歉，AI暂时无法回复")

        except Exception as e:
            logger.error(f"DZMM插件: 处理聊天时发生错误: {str(e)}")
            yield event.plain_result(f"处理聊天时发生错误: {str(e)}")

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE)
    async def handle_message(self, event: AstrMessageEvent, content: str = None):
        if not self.reply_to_at:
            return
        msg_obj = event.message_obj
        bot_id = msg_obj.self_id
        is_at_me = False
        for comp in msg_obj.message:
            # 判断消息是否At了机器人
            if isinstance(comp, Comp.At):
                if str(comp.qq) == str(bot_id):
                    is_at_me = True
                    break
        if not is_at_me:
            return
        #手动构建不含replay和at的消息文本
        if not content or content.strip() == "":
            content = ""
            for msg_obj in event.message_obj.message:
                if msg_obj.type == "Plain":
                    content += msg_obj.text
        async for result in self.dzmm_chat(event, content):
            yield result
                
    @command("dzmm_personas")
    async def dzmm_personas(self, event: AstrMessageEvent):
        """列出所有可用角色"""
        user_key = self.get_user_key(event)

        # 调试信息
        logger.info(f"DZMM插件: 用户查询角色列表，当前有 {len(self.personas)} 个角色")

        if not self.personas:
            yield event.plain_result("❌ 未配置任何角色，请检查配置")
            return

        persona_list = "\n".join([f"• {name}" for name in self.personas.keys()])
        current_persona = self.user_current_persona[user_key]
        yield event.plain_result(f"可用角色列表（共{len(self.personas)}个）：\n{persona_list}\n\n当前使用角色：{current_persona}")

    @command("dzmm_persona")
    async def dzmm_persona(self, event: AstrMessageEvent, persona_name: str = None):
        """切换角色"""
        user_key = self.get_user_key(event)

        if not persona_name or not persona_name.strip():
            available_personas = ", ".join(self.personas.keys())
            yield event.plain_result(f"请指定角色名称\n使用方法: /dzmm_persona [角色名]\n可用角色：{available_personas}")
            return

        persona_name = persona_name.strip()
        logger.info(f"DZMM插件: 尝试切换到角色 '{persona_name}'")

        if persona_name in self.personas:
            self.user_current_persona[user_key] = persona_name
            # 切换角色时清除上下文，避免角色混乱
            self.user_contexts[user_key].clear()
            
            # 保存角色和上下文到存储（如果启用记忆功能）
            if self.enable_memory and self.data_storage:
                self.data_storage.save_user_current_persona(self.user_current_persona)
                self.data_storage.save_user_contexts(self.user_contexts)
            
            logger.info(f"DZMM插件: 成功切换到角色 '{persona_name}'")
            yield event.plain_result(f"✅ 已切换到角色：{persona_name}\n\n💡 已自动清除聊天上下文以避免角色混乱")
        else:
            available_personas = ", ".join(self.personas.keys())
            logger.warning(f"DZMM插件: 角色 '{persona_name}' 不存在，可用角色: {available_personas}")
            yield event.plain_result(f"❌ 角色 '{persona_name}' 不存在\n可用角色：{available_personas}")

    @command("dzmm_keyls")
    async def dzmm_keyls(self, event: AstrMessageEvent):
        """列出所有API密钥及其使用状态"""
        user_key = self.get_user_key(event)

        key_status_list = []
        for name in self.api_keys.keys():
            failure_count = self.api_key_failures.get(name, 0)
            if failure_count < self.max_failures_before_switch:
                status = f"🟢正常（失败次数：{failure_count}/{failure_count}）"
            else:
                status = f"🔴无效（失败次数：{failure_count}/{failure_count}）"
            key_status_list.append(f"• {name} - {status}")
        
        key_list = "\n".join(key_status_list)
        current_key = self.user_current_api_key[user_key]
        yield event.plain_result(f"API密钥状态列表：\n{key_list}\n\n当前使用密钥：{current_key}\n\n说明：失败{self.max_failures_before_switch}次后密钥将被禁用并自动切换下一个密钥。密钥将会在次日01:00重置为可用。")

    @command("dzmm_key")
    async def dzmm_key(self, event: AstrMessageEvent, key_name: str = None):
        """切换API密钥"""
        user_key = self.get_user_key(event)

        if not key_name or not key_name.strip():
            available_keys = ", ".join(self.api_keys.keys())
            yield event.plain_result(f"请指定API密钥名称\n使用方法: /dzmm_key [密钥名]\n可用密钥：{available_keys}")
            return

        key_name = key_name.strip()
        logger.info(f"DZMM插件: 尝试切换到API密钥 '{key_name}'")

        if key_name in self.api_keys:
            self.user_current_api_key[user_key] = key_name
            
            # 保存用户当前API密钥到存储（如果启用记忆功能）
            if self.enable_memory and self.data_storage:
                self.data_storage.save_user_current_api_key(self.user_current_api_key)
            
            logger.info(f"DZMM插件: 成功切换到API密钥 '{key_name}'")
            yield event.plain_result(f"✅ 已切换到API密钥：{key_name}")
        else:
            available_keys = ", ".join(self.api_keys.keys())
            logger.warning(f"DZMM插件: API密钥 '{key_name}' 不存在，可用密钥: {available_keys}")
            yield event.plain_result(f"❌ API密钥 '{key_name}' 不存在\n可用密钥：{available_keys}")

    @command("dzmm_status")
    async def dzmm_status(self, event: AstrMessageEvent):
        """显示当前状态"""
        user_key = self.get_user_key(event)
        nickname = self.get_user_nickname(event)

        current_persona = self.user_current_persona[user_key]
        current_key = self.user_current_api_key[user_key]
        context_count = len(self.user_contexts[user_key])

        # 判断聊天模式
        group_id = event.get_group_id()

        if group_id and group_id != "private":
            if self.group_shared_context:
                chat_mode = "群聊模式（共享上下文）"
            else:
                chat_mode = "群聊模式（独立上下文）"
        else:
            chat_mode = "私聊模式"

        nickname_status = "启用" if self.show_nickname else "禁用"

        yield event.plain_result(
            f"当前状态：\n"
            f"• 聊天模式：{chat_mode}\n"
            f"• 当前用户：{nickname}\n"
            f"• 昵称显示：{nickname_status}\n"
            f"• 使用角色：{current_persona}\n"
            f"• 使用API密钥：{current_key}\n"
            f"• 上下文消息数：{context_count}/{self.context_length}"
        )

    @command("dzmm_clear")
    async def dzmm_clear(self, event: AstrMessageEvent):
        """清除聊天上下文"""
        user_key = self.get_user_key(event)

        self.user_contexts[user_key].clear()
        
        # 保存清除后的上下文到存储（如果启用记忆功能）
        if self.enable_memory and self.data_storage:
            self.data_storage.save_user_contexts(self.user_contexts)
        
        yield event.plain_result("✅ 已清除聊天上下文")
    

    
    @command("dzmm_resetkeys")
    async def dzmm_resetkeys(self, event: AstrMessageEvent):
        """重置所有API密钥的失败计数"""
        self.api_key_failures.clear()
        # 清除持久化存储中的失败计数（如果启用记忆功能）
        if self.enable_memory and self.data_storage:
            self.data_storage.clear_api_key_failures()
        logger.info("DZMM插件: 手动重置了所有API密钥的失败计数")
        yield event.plain_result("✅ 已重置所有API密钥的失败计数，所有密钥现在都可用")
    
    @command("dzmm_trigger_status")
    async def dzmm_trigger_status(self, event: AstrMessageEvent):
        """显示定时触发功能状态"""
        if not self.enable_auto_trigger:
            yield event.plain_result("❌ 定时触发功能未启用")
            return
        
        user_key = self.get_user_key(event)
        user_id = event.get_sender_id()
        
        # 检查是否为私聊
        group_id = event.get_group_id()
        if group_id and group_id != "private":
            yield event.plain_result("⚠️ 定时触发功能仅在私聊中有效")
            return
        
        # 检查白名单状态
        in_whitelist = user_id in self.auto_trigger_whitelist if self.auto_trigger_whitelist else False
        whitelist_status = "✅ 已加入" if in_whitelist else "❌ 未加入"
        
        # 获取最后活动时间
        last_activity = self.user_last_activity.get(user_key)
        if last_activity:
            last_activity_str = datetime.fromtimestamp(last_activity).strftime("%Y-%m-%d %H:%M:%S")
            minutes_since = (datetime.now().timestamp() - last_activity) / 60
            next_trigger_minutes = max(0, self.auto_trigger_interval - minutes_since)
        else:
            last_activity_str = "无记录"
            next_trigger_minutes = 0
        
        yield event.plain_result(
            f"定时触发功能状态：\n"
            f"• 功能状态：✅ 已启用\n"
            f"• 触发间隔：{self.auto_trigger_interval}分钟\n"
            f"• 白名单状态：{whitelist_status}\n"
            f"• 最后活动时间：{last_activity_str}\n"
            f"• 下次触发时间：{next_trigger_minutes:.1f}分钟后\n"
            f"• 触发消息：{self.auto_trigger_message}\n\n"
            f"💡 只有私聊且在白名单中的用户才会收到定时触发消息"
        )

    async def terminate(self):
        """插件卸载/停用时调用，用于清理资源"""
        logger.info("DZMM插件: 开始清理资源...")
        
        # 取消定时触发任务
        if hasattr(self, 'auto_trigger_task') and self.auto_trigger_task and not self.auto_trigger_task.done():
            self.auto_trigger_task.cancel()
            try:
                await self.auto_trigger_task
            except asyncio.CancelledError:
                logger.info("DZMM插件: 定时触发任务已取消")
            except Exception as e:
                logger.error(f"DZMM插件: 取消定时触发任务时发生错误: {str(e)}")
        
        # 保存所有数据（如果启用记忆功能）
        if hasattr(self, 'enable_memory') and self.enable_memory and hasattr(self, 'data_storage') and self.data_storage:
            try:
                self.data_storage.save_all_data(
                    self.user_contexts,
                    self.user_current_persona,
                    self.user_current_api_key,
                    self.api_key_failures,
                    user_last_activity=self.user_last_activity
                )
                logger.info("DZMM插件: 已保存所有数据")
            except Exception as e:
                logger.error(f"DZMM插件: 保存数据时发生错误: {str(e)}")
        
        logger.info("DZMM插件: 资源清理完成")

    def __del__(self):
        """析构函数，确保数据被保存并清理资源"""
        logger.info("DZMM插件: 开始清理资源...")
        
        # 取消定时触发任务
        if hasattr(self, 'auto_trigger_task') and self.auto_trigger_task and not self.auto_trigger_task.done():
            self.auto_trigger_task.cancel()
            logger.info("DZMM插件: 定时触发任务已取消")
        
        # 保存所有数据（如果启用记忆功能）
        if hasattr(self, 'enable_memory') and self.enable_memory and hasattr(self, 'data_storage') and self.data_storage:
            try:
                self.data_storage.save_all_data(
                    self.user_contexts,
                    self.user_current_persona,
                    self.user_current_api_key,
                    self.api_key_failures,
                    user_last_activity=self.user_last_activity
                )
                logger.info("DZMM插件: 已保存所有数据")
            except Exception as e:
                logger.error(f"DZMM插件: 保存数据时发生错误: {str(e)}")
        
        logger.info("DZMM插件: 资源清理完成")
