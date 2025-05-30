# DZMM插件使用示例

本文档提供了DZMM插件新功能的详细使用示例。

## 基本配置示例

### 完整配置示例

在astrbot的插件配置界面中，需要将JSON对象作为字符串填入：

**personas字段**：
```
{"default": "你是一个有帮助的AI助手。", "programmer": "你是一个专业的程序员，擅长解决编程问题和代码优化。精通Python、JavaScript、Java等多种编程语言。", "teacher": "你是一个耐心的老师，善于用简单易懂的方式解释复杂概念。你会根据学生的理解程度调整解释的深度。", "translator": "你是一个专业的翻译，能够准确翻译中英文、日文等多种语言，并保持原文的语调和风格。", "creative": "你是一个富有创意的作家，善于创作故事、文案和创意内容。你的回答充满想象力和艺术感。", "analyst": "你是一个数据分析师，擅长分析数据、发现趋势和提供基于数据的见解。"}
```

**api_keys字段**：
```
{"default": "sk-your-primary-key-here", "backup": "sk-your-backup-key-here", "premium": "sk-your-premium-key-with-higher-quota", "test": "sk-your-test-key-for-development"}
```

**其他配置**：
- context_length: 10
- temperature: 0.7
- max_tokens: 800

> **注意**：在astrbot配置界面中，personas和api_keys字段需要填入有效的JSON字符串格式。如果JSON格式不正确，插件会使用默认配置并在日志中显示警告。

## 使用场景示例

### 场景1：编程助手

```
用户: /dzmm_persona programmer
机器人: ✅ 已切换到角色：programmer
角色描述：你是一个专业的程序员，擅长解决编程问题和代码优化。精通Python、JavaScript、Java等多种编程语言。

💡 已自动清除聊天上下文以避免角色混乱

用户: /dzmm 帮我写一个Python函数，计算斐波那契数列
机器人: 好的！我来为你写一个计算斐波那契数列的Python函数...
```

### 场景2：学习助手

```
用户: /dzmm_persona teacher
机器人: ✅ 已切换到角色：teacher
角色描述：你是一个耐心的老师，善于用简单易懂的方式解释复杂概念。

用户: /dzmm 请解释一下什么是机器学习
机器人: 好的，让我用简单的方式来解释机器学习...
```

### 场景3：翻译助手

```
用户: /dzmm_persona translator
机器人: ✅ 已切换到角色：translator

用户: /dzmm 请将以下中文翻译成英文：人工智能正在改变我们的生活方式
机器人: Artificial intelligence is changing our way of life.
```

### 场景4：群聊协作

```
小明: /dzmm 我们来讨论一下这个项目的架构设计
机器人: 好的！我很乐意帮助大家讨论项目架构设计。请告诉我这个项目的基本情况...

小红: /dzmm 这是一个电商网站，需要支持高并发
机器人: @小红 了解了，电商网站确实需要考虑高并发问题。@小明 你们考虑使用什么技术栈呢？

小李: /dzmm 我建议使用微服务架构
机器人: @小李 微服务架构是个不错的选择！结合@小红提到的高并发需求和@小明提出的架构讨论，我建议...
```

### 场景5：API密钥管理

```
用户: /dzmm_keyls
机器人: 可用API密钥列表：
• default
• backup
• premium
• test

当前使用密钥：default

用户: /dzmm_key premium
机器人: ✅ 已切换到API密钥：premium

用户: /dzmm_status
机器人: 当前状态：
• 使用角色：translator
• 角色描述：你是一个专业的翻译，能够准确翻译中英文、日文等多种语言
• 使用API密钥：premium
• 上下文消息数：2/10
```

## 管理命令示例

### 查看所有可用角色

```
用户: /dzmm_personas
机器人: 可用角色列表：
• default: 你是一个有帮助的AI助手。
• programmer: 你是一个专业的程序员，擅长解决编程问题和代码优化。精通Python、JavaScript、Java等多种编程语言。
• teacher: 你是一个耐心的老师，善于用简单易懂的方式解释复杂概念。你会根据学生的理解程度调整解释的深度。
• translator: 你是一个专业的翻译，能够准确翻译中英文、日文等多种语言，并保持原文的语调和风格。
• creative: 你是一个富有创意的作家，善于创作故事、文案和创意内容。你的回答充满想象力和艺术感。
• analyst: 你是一个数据分析师，擅长分析数据、发现趋势和提供基于数据的见解。

当前使用角色：default
```

### 状态查看

```
用户: /dzmm_status
机器人: 当前状态：
• 使用角色：programmer
• 角色描述：你是一个专业的程序员，擅长解决编程问题和代码优化。精通Python、JavaScript、Java等多种编程语言。
• 使用API密钥：premium
• 上下文消息数：5/10
```

### 清除上下文

```
用户: /dzmm_clear
机器人: ✅ 已清除聊天上下文
```

## 错误处理示例

### 切换到不存在的角色

```
用户: /dzmm_persona doctor
机器人: ❌ 角色 'doctor' 不存在
可用角色：default, programmer, teacher, translator, creative, analyst
```

### 切换到不存在的API密钥

```
用户: /dzmm_key nonexistent
机器人: ❌ API密钥 'nonexistent' 不存在
可用密钥：default, backup, premium, test
```

## 最佳实践

1. **角色切换时机**：建议在开始新的对话主题时切换角色，以获得最佳的AI回复效果。

2. **API密钥管理**：
   - 使用 `default` 作为主要密钥
   - 配置 `backup` 密钥以防主密钥额度不足
   - 使用 `premium` 密钥处理重要任务
   - 使用 `test` 密钥进行开发测试

3. **上下文管理**：
   - 角色切换会自动清除上下文，这是为了避免角色混乱
   - 如果需要保持上下文，请在同一角色下继续对话
   - 使用 `/dzmm clear` 手动清除上下文以开始新话题

4. **配置建议**：
   - 根据实际使用场景配置角色
   - 为不同用途配置不同的API密钥
   - 合理设置 `context_length` 以平衡对话连贯性和API成本
