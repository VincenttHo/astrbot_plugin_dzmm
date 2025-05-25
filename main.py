from astrbot.api.event import AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.all import *

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


@register(
    "astrbot_plugin_dzmm",
    "Assistant",
    "Astrbot AI聊天插件，支持上下文对话、多角色和多API密钥配置",
    "1.0.1",
    "https://github.com/user/astrbot_plugin_dzmm",
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

        # 用户上下文存储 - 使用用户ID+群组ID作为键
        self.user_contexts: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.context_length))

        # 用户当前使用的角色和API密钥
        self.user_current_persona: Dict[str, str] = defaultdict(lambda: "default")
        self.user_current_api_key: Dict[str, str] = defaultdict(lambda: "default")

        # 验证API密钥
        if not self.api_keys or not any(self.api_keys.values()):
            logger.warning("DZMM插件: 未配置API密钥，插件将无法正常工作")

        # 调试信息：输出解析后的配置
        logger.info(f"DZMM插件: 已加载 {len(self.personas)} 个角色: {list(self.personas.keys())}")
        logger.info(f"DZMM插件: 已加载 {len(self.api_keys)} 个API密钥: {list(self.api_keys.keys())}")

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

    def get_user_key(self, event: AstrMessageEvent) -> str:
        """生成用户唯一标识"""
        user_id = event.get_sender_id() or "unknown"
        group_id = event.get_group_id() or "private"
        platform = event.get_platform_name() or "unknown"
        return f"{platform}_{group_id}_{user_id}"

    def add_to_context(self, user_key: str, role: str, content: str):
        """添加消息到用户上下文"""
        self.user_contexts[user_key].append({"role": role, "content": content})

    def get_context_messages(self, user_key: str) -> List[dict]:
        """获取用户的上下文消息"""
        # 获取用户当前使用的角色
        current_persona = self.user_current_persona[user_key]
        system_prompt = self.personas.get(current_persona, self.personas.get("default", "你是一个有帮助的AI助手。"))

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(list(self.user_contexts[user_key]))
        return messages

    def get_current_api_key(self, user_key: str) -> str:
        """获取用户当前使用的API密钥"""
        current_key_name = self.user_current_api_key[user_key]
        return self.api_keys.get(current_key_name, self.api_keys.get("default", ""))

    def _sync_chat_with_ai(self, messages: List[dict], api_key: str) -> Optional[str]:
        """同步版本的AI聊天函数，支持完整的消息历史"""
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
                return "".join(all_content_parts)
            else:
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"DZMM插件: 请求错误: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"DZMM插件: 发生未知错误: {str(e)}")
            return None

    async def chat_with_ai(self, messages: List[dict], user_key: str) -> Optional[str]:
        """调用AI接口进行聊天"""
        api_key = self.get_current_api_key(user_key)
        if not api_key:
            return "错误：未配置API密钥，请联系管理员配置插件"

        try:
            # 在线程池中运行同步函数
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                result = await loop.run_in_executor(
                    executor,
                    lambda: self._sync_chat_with_ai(messages, api_key)
                )

            return result if result else "抱歉，没有收到AI的回复"

        except Exception as e:
            logger.error(f"DZMM插件: 调用AI接口时发生错误: {str(e)}")
            return f"调用AI接口时发生错误: {str(e)}"

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
                "/dzmm_keyls - 列出所有API密钥\n"
                "/dzmm_key [密钥名] - 切换API密钥\n"
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
            yield event.plain_result(
                "DZMM AI聊天插件帮助：\n"
                "\n基础命令：\n"
                "• /dzmm [内容] - 与AI聊天，支持上下文对话\n"
                "• /dzmm help - 显示此帮助信息\n"
                "\n管理命令：\n"
                "• /dzmm_personas - 列出所有可用角色\n"
                "• /dzmm_persona [角色名] - 切换到指定角色\n"
                "• /dzmm_keyls - 列出所有可用API密钥\n"
                "• /dzmm_key [密钥名] - 切换到指定API密钥\n"
                "• /dzmm_status - 显示当前状态\n"
                "• /dzmm_clear - 清除聊天上下文\n\n"
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
        # 添加用户消息到上下文
        self.add_to_context(user_key, "user", content)

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
            logger.info(f"DZMM插件: 成功切换到角色 '{persona_name}'")
            yield event.plain_result(f"✅ 已切换到角色：{persona_name}\n\n💡 已自动清除聊天上下文以避免角色混乱")
        else:
            available_personas = ", ".join(self.personas.keys())
            logger.warning(f"DZMM插件: 角色 '{persona_name}' 不存在，可用角色: {available_personas}")
            yield event.plain_result(f"❌ 角色 '{persona_name}' 不存在\n可用角色：{available_personas}")

    @command("dzmm_keyls")
    async def dzmm_keyls(self, event: AstrMessageEvent):
        """列出所有可用API密钥"""
        user_key = self.get_user_key(event)

        key_list = "\n".join([f"• {name}" for name in self.api_keys.keys()])
        current_key = self.user_current_api_key[user_key]
        yield event.plain_result(f"可用API密钥列表：\n{key_list}\n\n当前使用密钥：{current_key}")

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

        current_persona = self.user_current_persona[user_key]
        current_key = self.user_current_api_key[user_key]
        context_count = len(self.user_contexts[user_key])
        yield event.plain_result(
            f"当前状态：\n"
            f"• 使用角色：{current_persona}\n"
            f"• 使用API密钥：{current_key}\n"
            f"• 上下文消息数：{context_count}/{self.context_length}"
        )

    @command("dzmm_clear")
    async def dzmm_clear(self, event: AstrMessageEvent):
        """清除聊天上下文"""
        user_key = self.get_user_key(event)

        self.user_contexts[user_key].clear()
        yield event.plain_result("✅ 已清除聊天上下文")
