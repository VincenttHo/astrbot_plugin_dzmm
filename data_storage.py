import json
import os
from typing import Dict, List, Optional, Any
from collections import defaultdict, deque
from astrbot.api import logger
import threading
import time
from datetime import datetime


class DataStorage:
    """数据持久化存储类，用于保存用户上下文、密钥失败计数等信息"""
    
    def __init__(self, plugin_name: str = "astrbot_plugin_dzmm"):
        self.plugin_name = plugin_name
        self.data_dir = os.path.join("data", "plugins", plugin_name)
        self.data_file = os.path.join(self.data_dir, "plugin_data.json")
        self.lock = threading.Lock()
        
        # 确保数据目录存在
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 初始化数据结构
        self.data = {
            "user_contexts": {},
            "user_current_persona": {},
            "user_current_api_key": {},
            "api_key_failures": {},
            "user_last_activity": {},
            "last_save_time": None,
            "version": "1.0.1"
        }
        
        # 加载已保存的数据
        self.load_data()
        
        # 启动自动保存线程
        self._start_auto_save()
    
    def load_data(self) -> bool:
        """从文件加载数据"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    
                # 合并加载的数据，保持默认结构
                for key in self.data.keys():
                    if key in loaded_data:
                        self.data[key] = loaded_data[key]
                        
                logger.info(f"DZMM插件: 成功加载数据文件，包含 {len(self.data['user_contexts'])} 个用户上下文")
                return True
            else:
                logger.info("DZMM插件: 数据文件不存在，使用默认数据结构")
                return False
                
        except Exception as e:
            logger.error(f"DZMM插件: 加载数据文件失败: {str(e)}")
            return False
    
    def save_data(self) -> bool:
        """保存数据到文件"""
        try:
            with self.lock:
                # 更新保存时间
                self.data["last_save_time"] = datetime.now().isoformat()
                
                # 创建临时文件，避免写入过程中数据损坏
                temp_file = self.data_file + ".tmp"
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, ensure_ascii=False, indent=2)
                
                # 原子性替换文件
                if os.path.exists(self.data_file):
                    os.replace(temp_file, self.data_file)
                else:
                    os.rename(temp_file, self.data_file)
                    
                logger.debug("DZMM插件: 数据已保存到文件")
                return True
                
        except Exception as e:
            logger.error(f"DZMM插件: 保存数据文件失败: {str(e)}")
            return False
    
    def _async_save(self):
        """异步保存数据到文件"""
        def save_worker():
            self.save_data()
        
        save_thread = threading.Thread(target=save_worker, daemon=True)
        save_thread.start()
    
    def save_all_data(self, user_contexts, user_current_persona, user_current_api_key, api_key_failures, user_last_activity=None):
        """保存所有数据"""
        # 将deque转换为list进行JSON序列化
        contexts_data = {}
        for user_key, messages in user_contexts.items():
            contexts_data[user_key] = list(messages)
        
        self.data["user_contexts"] = contexts_data
        self.data["user_current_persona"] = dict(user_current_persona)
        self.data["user_current_api_key"] = dict(user_current_api_key)
        self.data["api_key_failures"] = dict(api_key_failures)
        if user_last_activity is not None:
            self.data["user_last_activity"] = dict(user_last_activity)
        
        # 立即保存到文件
        self.save_data()
    
    def get_user_contexts(self, context_length: int) -> Dict[str, deque]:
        """获取用户上下文，转换为deque格式"""
        contexts = defaultdict(lambda: deque(maxlen=context_length))
        
        for user_key, messages in self.data["user_contexts"].items():
            # 创建新的deque并添加消息
            user_deque = deque(maxlen=context_length)
            for msg in messages[-context_length:]:  # 只取最新的消息
                user_deque.append(msg)
            contexts[user_key] = user_deque
            
        return contexts
    
    def save_user_contexts(self, user_contexts: Dict[str, deque]):
        """保存用户上下文"""
        # 将deque转换为list进行JSON序列化
        contexts_data = {}
        for user_key, messages in user_contexts.items():
            contexts_data[user_key] = list(messages)
        
        self.data["user_contexts"] = contexts_data
        # 立即异步保存到文件
        self._async_save()
    
    def get_user_current_persona(self) -> Dict[str, str]:
        """获取用户当前角色"""
        return defaultdict(lambda: "default", self.data["user_current_persona"])
    
    def save_user_current_persona(self, user_current_persona: Dict[str, str]):
        """保存用户当前角色"""
        self.data["user_current_persona"] = dict(user_current_persona)
        # 立即异步保存到文件
        self._async_save()
    
    def get_user_current_api_key(self) -> Dict[str, str]:
        """获取用户当前API密钥"""
        return defaultdict(lambda: "default", self.data["user_current_api_key"])
    
    def save_user_current_api_key(self, user_current_api_key: Dict[str, str]):
        """保存用户当前API密钥"""
        self.data["user_current_api_key"] = dict(user_current_api_key)
        # 立即异步保存到文件
        self._async_save()
    
    def get_api_key_failures(self) -> Dict[str, int]:
        """获取API密钥失败计数"""
        return defaultdict(int, self.data["api_key_failures"])
    
    def save_api_key_failures(self, api_key_failures: Dict[str, int]):
        """保存API密钥失败计数"""
        self.data["api_key_failures"] = dict(api_key_failures)
        # 立即异步保存到文件
        self._async_save()
    
    def clear_api_key_failures(self):
        """清除所有API密钥失败计数"""
        self.data["api_key_failures"] = {}
        # 立即异步保存到文件
        self._async_save()
    
    def get_user_last_activity(self) -> Dict[str, str]:
        """获取用户最后活动时间"""
        return dict(self.data.get("user_last_activity", {}))
    
    def save_user_last_activity(self, user_last_activity: Dict[str, str]):
        """保存用户最后活动时间"""
        self.data["user_last_activity"] = dict(user_last_activity)
        # 立即异步保存到文件
        self._async_save()
    
    def clear_user_context(self, user_key: str):
        """清除指定用户的上下文"""
        if user_key in self.data["user_contexts"]:
            del self.data["user_contexts"][user_key]
            # 立即异步保存到文件
            self._async_save()
    
    def clear_all_contexts(self):
        """清除所有用户上下文"""
        self.data["user_contexts"] = {}
        # 立即异步保存到文件
        self._async_save()
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        return {
            "total_users": len(self.data["user_contexts"]),
            "total_messages": sum(len(msgs) for msgs in self.data["user_contexts"].values()),
            "failed_keys": len([k for k, v in self.data["api_key_failures"].items() if v > 0]),
            "last_save_time": self.data["last_save_time"],
            "data_file_size": os.path.getsize(self.data_file) if os.path.exists(self.data_file) else 0,
            "version": self.data["version"]
        }
    
    def _start_auto_save(self):
        """启动自动保存线程"""
        def auto_save_worker():
            while True:
                time.sleep(300)  # 每5分钟自动保存一次
                self.save_data()
        
        auto_save_thread = threading.Thread(target=auto_save_worker, daemon=True)
        auto_save_thread.start()
        logger.info("DZMM插件: 自动保存线程已启动，每5分钟保存一次数据")
    
    def backup_data(self) -> bool:
        """创建数据备份"""
        try:
            if os.path.exists(self.data_file):
                backup_file = f"{self.data_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                import shutil
                shutil.copy2(self.data_file, backup_file)
                logger.info(f"DZMM插件: 数据备份已创建: {backup_file}")
                return True
            return False
        except Exception as e:
            logger.error(f"DZMM插件: 创建数据备份失败: {str(e)}")
            return False
    
    def cleanup_old_backups(self, keep_count: int = 5):
        """清理旧的备份文件，只保留最新的几个"""
        try:
            backup_files = []
            for file in os.listdir(self.data_dir):
                if file.startswith("plugin_data.json.backup."):
                    backup_files.append(os.path.join(self.data_dir, file))
            
            # 按修改时间排序，保留最新的几个
            backup_files.sort(key=os.path.getmtime, reverse=True)
            
            for old_backup in backup_files[keep_count:]:
                os.remove(old_backup)
                logger.debug(f"DZMM插件: 已删除旧备份文件: {old_backup}")
                
        except Exception as e:
            logger.error(f"DZMM插件: 清理备份文件失败: {str(e)}")