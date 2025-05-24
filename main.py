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
    "Astrbot AI聊天插件，支持上下文对话和自定义配置",
    "1.0.0",
    "https://github.com/user/astrbot_plugin_dzmm",
)
class PluginDzmm(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config

        # 配置参数
        self.api_key = self.config.get("api_key", "")
        self.system_prompt = self.config.get("system_prompt", "你是一个有帮助的AI助手。")
        self.context_length = self.config.get("context_length", 10)
        self.api_url = self.config.get("api_url", "https://www.gpt4novel.com/api/xiaoshuoai/ext/v1/chat/completions")
        self.model = self.config.get("model", "nalang-turbo-v23")
        self.temperature = self.config.get("temperature", 0.7)
        self.max_tokens = self.config.get("max_tokens", 800)
        self.top_p = self.config.get("top_p", 0.35)
        self.repetition_penalty = self.config.get("repetition_penalty", 1.05)

        # 用户上下文存储 - 使用用户ID+群组ID作为键
        self.user_contexts: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.context_length))

        # 验证API密钥
        if not self.api_key:
            logger.warning("DZMM插件: 未配置API密钥，插件将无法正常工作")

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
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(list(self.user_contexts[user_key]))
        return messages

    def _sync_chat_with_ai(self, messages: List[dict]) -> Optional[str]:
        """同步版本的AI聊天函数，支持完整的消息历史"""
        import requests
        import json

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
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

    async def chat_with_ai(self, messages: List[dict]) -> Optional[str]:
        """调用AI接口进行聊天"""
        if not self.api_key:
            return "错误：未配置API密钥，请联系管理员配置插件"

        try:
            # 在线程池中运行同步函数
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                result = await loop.run_in_executor(
                    executor,
                    lambda: self._sync_chat_with_ai(messages)
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
                "/dzmm clear - 清除聊天上下文\n"
                "/dzmm help - 显示帮助信息"
            )
            return

        content = content.strip()

        # 处理特殊命令
        if content.lower() == "help":
            yield event.plain_result(
                "DZMM AI聊天插件帮助：\n"
                "• /dzmm [内容] - 与AI聊天，支持上下文对话\n"
                "• /dzmm clear - 清除当前用户的聊天上下文\n"
                "• /dzmm help - 显示此帮助信息\n\n"
                f"当前配置：\n"
                f"• 上下文长度：{self.context_length}条消息\n"
                f"• 模型：{self.model}\n"
                f"• 温度：{self.temperature}"
            )
            return

        if content.lower() == "clear":
            user_key = self.get_user_key(event)
            self.user_contexts[user_key].clear()
            yield event.plain_result("✅ 已清除聊天上下文")
            return

        # 获取用户标识和上下文
        user_key = self.get_user_key(event)

        # 添加用户消息到上下文
        self.add_to_context(user_key, "user", content)

        # 获取完整的消息列表
        messages = self.get_context_messages(user_key)

        # 调用AI接口
        try:
            ai_response = await self.chat_with_ai(messages)

            if ai_response:
                # 添加AI回复到上下文
                self.add_to_context(user_key, "assistant", ai_response)
                yield event.plain_result(ai_response)
            else:
                yield event.plain_result("抱歉，AI暂时无法回复")

        except Exception as e:
            logger.error(f"DZMM插件: 处理聊天时发生错误: {str(e)}")
            yield event.plain_result(f"处理聊天时发生错误: {str(e)}")
