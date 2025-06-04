<div align="center">

![:name](https://count.getloli.com/@astrbot_plugin_dzmm?name=astrbot_plugin_dzmm&theme=nixietube-1&padding=7&offset=0&align=top&scale=1&pixelated=1&darkmode=auto)

</div>


# astrbot_plugin_dzmm

DZMM聊天插件，支持上下文对话和自定义配置。默认使用dzmm的免费试用模型nalang-turbo-v23，能每天50条消息。

## DZMM是什么？

DZMM（网址：dzmm.ai）是一个中文AI角色扮演平台，融合先进AI技术与创意写作，旨在为用户提供沉浸式的角色互动体验。

它旗下所自研的模型：Nalang针对角色扮演进行优化，有如下优点：
- ✅ 中文优化好：对中文语境理解优于多数开源模型，适合角色扮演类场景。
- ✅ 长记忆能力：支持较长上下文对话，保持人设稳定。
- ✅ 情绪表达自然：角色语气丰富，情绪细腻，适合沉浸式对话。
- ✅ 训练在国内语料上：对网络流行语、常见角色设定接受度高。
- ✅ 可以进行一些不可描述的互动（你懂的）。

🔔 **它旗下的nalang-turbo-v23模型有每天免费额度，可以每天50条消息。**

使用效果图：

![使用效果图](https://raw.githubusercontent.com/VincenttHo/astrbot_plugin_dzmm/refs/heads/main/sample.jpg)

## 功能特点

- 🤖 支持与AI进行自然对话
- 💬 维持聊天上下文，支持连续对话
- 👥 **智能用户隔离**，支持群聊共享上下文和私聊独立上下文
- 🏷️ **昵称识别**，在群聊中显示用户昵称，帮助AI区分不同用户
- 🎭 **多角色支持**，可配置多个系统提示词并随时切换
- 🔑 **多API密钥支持**，可配置多个API密钥并随时切换
- ⚙️ 丰富的配置选项，支持自定义系统提示词
- 🔧 支持多种AI模型和参数调节

## 配置说明

### 必须配置 <font color='red'>（重要）</font>

#### API密钥配置 (api_keys)
api_key是用于访问DZMM模型的重要配置，支持多个key配置，采用json格式配置，例子如下：
```json
{
  "default": "your-primary-key-here",
  "backup": "your-backup-key-here",
  "premium": "your-premium-key-here"
}
```
🔔 **注意：key请在DZMM官网获取，获取界面在“充值”-“API”中**

#### 多角色配置 (personas)
在astrbot配置界面中，personas字段应该填入JSON字符串：
```json
{
  "default": "你是一个有帮助的AI助手。",
  "programmer": "你是一个专业的程序员，擅长解决编程问题和代码优化。",
  "teacher": "你是一个耐心的老师，善于用简单易懂的方式解释复杂概念。",
  "translator": "你是一个专业的翻译，能够准确翻译各种语言。",
  "creative": "你是一个富有创意的作家，善于创作故事和文案。"
}
```
🔔 **可以参考项目中的[sample_persona.json](https://github.com/VincenttHo/astrbot_plugin_dzmm/blob/main/sample_persona.json)，里面有我写好的一些角色卡，感兴趣的可以直接拿来用。**

### 可选配置

- **system_prompt**: 系统提示词，默认为"你是一个有帮助的AI助手。"
- **context_length**: 上下文消息数量，默认为10条
- **api_url**: API接口地址，默认为gpt4novel接口
- **model**: 使用的模型，默认为"nalang-turbo-v23"
- **temperature**: 温度参数（0-1），控制回复的随机性，默认0.7
- **max_tokens**: 最大token数，默认800
- **top_p**: Top-p参数（0-1），默认0.35
- **repetition_penalty**: 重复惩罚系数，默认1.05
- **show_nickname**: 在群聊中发送给AI时显示用户昵称，默认true
- **group_shared_context**: 群聊共享上下文，默认true

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

## 特性说明

### 多角色支持

- 支持配置多个命名的系统提示词（角色）
- 每个用户可以独立切换使用的角色
- 切换角色时会自动清除聊天上下文，避免角色混乱

### 多API密钥支持

- 支持配置多个命名的API密钥
- 每个用户可以独立切换使用的API密钥
- 支持在不同密钥之间无缝切换

### 智能用户隔离

插件支持两种上下文管理模式：

#### 群聊模式
- **共享上下文**（默认）：群内所有成员共享同一个聊天上下文，AI能够理解群聊的完整对话流程
- **独立上下文**：每个群成员都有独立的上下文，适合需要隐私保护的场景
- **昵称识别**：AI能够通过 `[昵称]: 消息内容` 的格式区分不同的发言者

#### 私聊模式
- 每个用户都有完全独立的聊天上下文
- 不显示昵称信息，保持简洁的对话体验

#### 配置选项
- `group_shared_context`: 控制群聊是否共享上下文（默认true）
- `show_nickname`: 控制是否在群聊中发送给AI时显示用户昵称（默认true）

### 上下文管理

- 自动维护指定数量的历史消息
- 超出限制时自动清理最旧的消息
- 支持手动清除上下文

### 错误处理

- API密钥未配置时会给出明确提示
- 网络错误时会自动重试
- 详细的错误日志记录

## 安装说明

#### 手动安装

1. 将插件文件放置到astrbot的插件目录
2. 在astrbot配置中启用插件
3. 配置API密钥和其他参数
4. 重启astrbot

#### 界面安装

在astrbot的Web管理界面中，进入"插件市场"页面，搜索"astrbot_plugin_dzmm"，点击安装按钮即可完成安装。

### 快速配置

- api_keys: `{"default": "你的主要密钥", "backup": "你的备用密钥"}`
- personas: `{"default": "你是一个有帮助的AI助手。", "programmer": "你是一个专业的程序员。"}`

> 💡 **提示**：可以使用 `config_helper.py` 工具生成正确的JSON配置字符串

## 注意事项

- 请确保API密钥有效且有足够的额度
- 上下文长度设置过大可能会增加API调用成本
- 建议根据实际需求调整温度和其他参数
- 插件已包含command装饰器的兼容性处理，支持不同版本的astrbot

## 版本历史

- v1.0.2: 新增智能用户隔离和昵称识别功能
  - 👥 支持群聊共享上下文和私聊独立上下文
  - 🏷️ 在群聊中显示用户昵称，帮助AI区分不同用户
  - ⚙️ 新增配置选项控制群聊模式和昵称显示
  - 📊 增强状态显示，显示聊天模式和昵称状态
- v1.0.1: 新增多角色和多API密钥支持
  - ✨ 支持多个系统提示词配置，可随时切换角色
  - 🔑 支持多个API密钥配置，可随时切换密钥
  - 📋 新增状态查看命令，显示当前使用的角色和密钥
  - 🔄 保持向后兼容，支持旧版本配置格式
- v1.0.0: 初始版本，支持基本聊天和上下文管理

## 许可证

MIT License
