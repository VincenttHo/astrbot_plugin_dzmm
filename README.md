<div align="center">

![:name](https://count.getloli.com/@astrbot_plugin_dzmm?name=astrbot_plugin_dzmm&theme=nixietube-1&padding=7&offset=0&align=top&scale=1&pixelated=1&darkmode=auto)

</div>


# astrbot_plugin_dzmm

DZMM聊天插件，支持上下文对话和自定义配置。默认使用dzmm的免费试用模型，能每天50条消息。

## 功能特点

- 🤖 支持与AI进行自然对话
- 💬 维持聊天上下文，支持连续对话
- 👥 用户隔离，每个用户都有独立的聊天上下文
- 🎭 **多角色支持**，可配置多个系统提示词并随时切换
- 🔑 **多API密钥支持**，可配置多个API密钥并随时切换
- ⚙️ 丰富的配置选项，支持自定义系统提示词
- 🔧 支持多种AI模型和参数调节

## 使用方法

### 基本命令

- `/dzmm [内容]` - 与AI聊天
- `/dzmm help` - 显示帮助信息
- `/dzmm clear` - 清除当前用户的聊天上下文

### 角色管理命令

- `/dzmm_personas` - 列出所有可用角色
- `/dzmm_persona [角色名]` - 切换到指定角色
- `/dzmm_status` - 显示当前使用的角色和API密钥状态

### API密钥管理命令

- `/dzmm_keyls` - 列出所有可用的API密钥名称
- `/dzmm_key [密钥名]` - 切换到指定API密钥
- `/dzmm_clear` - 清除聊天上下文（与 `/dzmm clear` 相同）

### 使用示例

```
# 基本聊天
/dzmm 你好，请介绍一下自己
/dzmm 刚才我们聊了什么？

# 角色切换
/dzmm_personas                    # 查看所有角色
/dzmm_persona programmer          # 切换到程序员角色
/dzmm 帮我写一个Python函数

# API密钥切换
/dzmm_keyls                       # 查看所有API密钥
/dzmm_key backup                  # 切换到备用API密钥

# 状态查看和清理
/dzmm_status                      # 查看当前状态
/dzmm_clear                       # 清除聊天上下文
```

## 配置说明

在astrbot的插件配置中，你可以设置以下参数：

### 必需配置

- **api_key**: OpenAI API密钥（必须配置，请自行在DZMM官网注册并获取，获取界面在“充值”-“API”中）

### 可选配置

- **system_prompt**: 系统提示词，默认为"你是一个有帮助的AI助手。"
- **context_length**: 上下文消息数量，默认为10条
- **api_url**: API接口地址，默认为gpt4novel接口
- **model**: 使用的模型，默认为"nalang-turbo-v23"
- **temperature**: 温度参数（0-1），控制回复的随机性，默认0.7
- **max_tokens**: 最大token数，默认800
- **top_p**: Top-p参数（0-1），默认0.35
- **repetition_penalty**: 重复惩罚系数，默认1.05

### 新功能配置

#### 多角色配置 (personas)
在astrbot配置界面中，personas字段应该填入JSON字符串：
```json
"{\"default\": \"你是一个有帮助的AI助手。\", \"programmer\": \"你是一个专业的程序员，擅长解决编程问题和代码优化。\", \"teacher\": \"你是一个耐心的老师，善于用简单易懂的方式解释复杂概念。\", \"translator\": \"你是一个专业的翻译，能够准确翻译各种语言。\", \"creative\": \"你是一个富有创意的作家，善于创作故事和文案。\"}"
```

或者更易读的格式（注意转义引号）：
```
{
  "default": "你是一个有帮助的AI助手。",
  "programmer": "你是一个专业的程序员，擅长解决编程问题和代码优化。",
  "teacher": "你是一个耐心的老师，善于用简单易懂的方式解释复杂概念。",
  "translator": "你是一个专业的翻译，能够准确翻译各种语言。",
  "creative": "你是一个富有创意的作家，善于创作故事和文案。"
}
```

#### 多API密钥配置 (api_keys)
在astrbot配置界面中，api_keys字段应该填入JSON字符串：
```json
"{\"default\": \"sk-your-primary-key-here\", \"backup\": \"sk-your-backup-key-here\", \"premium\": \"sk-your-premium-key-here\"}"
```

或者更易读的格式：
```
{
  "default": "sk-your-primary-key-here",
  "backup": "sk-your-backup-key-here",
  "premium": "sk-your-premium-key-here"
}
```

## 特性说明

### 多角色支持

- 支持配置多个命名的系统提示词（角色）
- 每个用户可以独立切换使用的角色
- 切换角色时会自动清除聊天上下文，避免角色混乱
- 兼容旧版本的 `system_prompt` 配置

### 多API密钥支持

- 支持配置多个命名的API密钥
- 每个用户可以独立切换使用的API密钥
- 支持在不同密钥之间无缝切换
- 兼容旧版本的 `api_key` 配置

### 用户隔离

插件会为每个用户维护独立的聊天上下文，用户标识由以下信息组成：
- 平台名称
- 群组ID（私聊时为"private"）
- 用户ID

### 上下文管理

- 自动维护指定数量的历史消息
- 超出限制时自动清理最旧的消息
- 支持手动清除上下文

### 错误处理

- API密钥未配置时会给出明确提示
- 网络错误时会自动重试
- 详细的错误日志记录

## 安装说明

1. 将插件文件放置到astrbot的插件目录
2. 在astrbot配置中启用插件
3. 配置API密钥和其他参数
4. 重启astrbot

### 快速配置

**最简配置**（仅配置API密钥）：
- api_key: `你的API密钥`

**推荐配置**（使用新功能）：
- api_keys: `{"default": "你的主要密钥", "backup": "你的备用密钥"}`
- personas: `{"default": "你是一个有帮助的AI助手。", "programmer": "你是一个专业的程序员。"}`

> 💡 **提示**：可以使用 `config_helper.py` 工具生成正确的JSON配置字符串

## 注意事项

- 请确保API密钥有效且有足够的额度
- 上下文长度设置过大可能会增加API调用成本
- 建议根据实际需求调整温度和其他参数
- 插件已包含command装饰器的兼容性处理，支持不同版本的astrbot

## 故障排除

### 常见问题

#### 1. 插件加载失败
如果遇到"cannot import name 'command'"错误：
- 插件已包含自动兼容处理
- 确保使用最新版本的插件代码
- 检查astrbot版本是否支持

#### 2. 命令无响应
- 确保使用正确的命令格式：`/dzmm [内容]`
- 检查API密钥配置是否正确
- 查看astrbot日志获取详细错误信息

#### 3. JSON配置解析失败
如果在日志中看到"JSON解析失败"的警告：
- 检查personas和api_keys字段的JSON格式是否正确
- 确保JSON字符串中的引号都已正确转义
- 可以使用提供的config_helper.py工具生成正确的配置
- 示例正确格式：`{"default": "你是一个助手", "programmer": "你是程序员"}`

#### 4. 角色或密钥切换失败
- 使用`/dzmm personas`和`/dzmm keyls`查看可用选项
- 确保角色名和密钥名拼写正确
- 角色名和密钥名区分大小写

## 版本历史

- v1.0.1: 新增多角色和多API密钥支持
  - ✨ 支持多个系统提示词配置，可随时切换角色
  - 🔑 支持多个API密钥配置，可随时切换密钥
  - 📋 新增状态查看命令，显示当前使用的角色和密钥
  - 🔄 保持向后兼容，支持旧版本配置格式
- v1.0.0: 初始版本，支持基本聊天和上下文管理

## 许可证

MIT License
