# 01 — 问题全貌：你遇到了什么

## 时间线还原

### 1. 切换模型

你通过 `/model` 命令切换到了 DeepSeek：

```bash
/model deepseek-v4-flash
```

系统提示切换成功：

```
Model switched to deepseek-v4-flash
Provider: custom
Context: 1,000,000 tokens
Warning: Auto-corrected deekseek-v4-flash → deepseek-v4-flash
```

### 2. 开始超时

之后每次对话，DeepSeek API 都不响应：

```
⚠️ No response from provider for 300s (model: deepseek-v4-flash, context: ~128,928 tokens). Reconnecting...
```

注意这里的关键信息：
- **300s** = 5 分钟无响应
- **context: ~128,928 tokens** = 上下文很大（约 129K tokens）
- **Reconnecting...** = 正在重连

### 3. 无限重连循环

系统开始反复重连，每次都等 5 分钟超时：

```
⏳ Still working... (10 min elapsed — iteration 1/90, waiting for stream response (270s, no chunks yet))
⏳ Still working... (20 min elapsed — iteration 1/90, waiting for stream response (240s, no chunks yet))
```

- `iteration 1/90` = 还在第 1 轮对话（`max_turns=90` 还没动）
- `waiting for stream response` = 在等 API 返回数据流
- `(270s, no chunks yet)` = 等了 270 秒，一个数据块都没收到

### 4. Gateway 重启

```
⚠️ Gateway restarting — Your current task will be interrupted.
```

Gateway（消息网关）检测到会话卡死，强制重启。

### 5. 会话丢失

```
◐ Session automatically reset (previous session was stopped or interrupted). Conversation history cleared.
Use /resume to browse and restore a previous session.
Adjust reset timing in config.yaml under session_reset.
```

重启后会话被自动重置，对话历史清空，模型回到了默认的 `qwen3.5-plus`。

---

## 为什么会这样？

### 根本原因：DeepSeek API 不稳定

`deepseek-v4-flash` 模型在处理大上下文（129K tokens）时响应极慢或根本不响应。这不是 Hermes 的 bug，是 API 端的问题。

### 直接原因：重试机制不智能

Hermes 的重试逻辑是这样的：

```
失败 → 等 5 秒 → 重试 → 再等 300 秒超时 → 失败 → 等 10 秒 → 重试 → ...
```

问题在于：
1. **重试次数硬编码为 3 次** — 你不能调整
2. **每次重试都要等 300 秒超时** — 3 次 = 15 分钟浪费
3. **没有 fallback 配置** — 即使配了 fallback，也要等 3 次重试用完才切换
4. **Gateway 不活跃超时 = 1800 秒** — 但重试期间的"等待"不算活跃

### 类比

就像你打电话给客服：
- 第 1 次：打通了但没人说话，等了 5 分钟挂断
- 等 5 秒后重拨
- 第 2 次：又没人说话，再等 5 分钟
- 等 10 秒后重拨
- 第 3 次：还是没人说话
- 此时已经过了 **15 分钟**

而一个更聪明的做法是：第 1 次发现没人说话，**立刻换另一个客服号码**。

---

## 这个问题别人也遇到过

GitHub Issue [#11616](https://github.com/NousResearch/hermes-agent/issues/11616) 的作者 HarmonClaw 遇到了几乎一样的情况：

```
[2026/4/17 20:12] ⚠️ No response from provider for 180s (model: qwen3-coder-480b-a35b-instruct)
[2026/4/17 20:13] ⏳ Retrying in 2.0s (attempt 1/3)...
[2026/4/17 20:16] ⚠️ No response from provider for 180s
[2026/4/17 20:17] ⏳ Retrying in 4.5s (attempt 2/3)...
...（重复了 30 分钟）
```

他的原文描述：

> unstalbe provider cause agent reconnect again and again, that is a waste of time.

（不稳定的 provider 导致 agent 一遍遍重连，浪费大量时间。）

---

## 好消息：这个问题已经被修复了

PR [#14730](https://github.com/NousResearch/hermes-agent/pull/14730) 在 **2026-04-23**（就在你遇到问题前两天）合并了 `api_max_retries` 配置项。

但你的 fork 还没有更新到这个改动。

详见 [05-issue-11616.md](05-issue-11616.md)。
