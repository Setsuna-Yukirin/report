# 02 — 配置项参考（说人话版）

> 所有配置都在 `~/.hermes/config.yaml` 中。以下按模块分类，只讲你真正会用到的。

---

## 一、`agent` — 代理核心行为

这个模块控制 Hermes Agent 的"大脑"怎么工作。

### `max_turns: 90`

**说人话**：一次对话最多允许模型调用 90 次工具。

**什么时候用**：如果你发现复杂任务做不完（比如要写很多文件、跑很多测试），可以调大。一般 90 足够了。

**源码位置**：`run_agent.py` 主循环 `while api_call_count < self.max_iterations`

---

### `gateway_timeout: 1800`

**说人话**：代理**完全不动**超过 30 分钟，Gateway 就会认为它卡死了，强制结束。

**关键细节**：
- 不是"总运行时间 30 分钟"，而是"**空闲** 30 分钟"
- 只要模型在调用工具、在返回数据，就不会超时
- 设 `0` = 永不超时

**源码位置**：`gateway/run.py:3197`

```python
_raw_stale_timeout = float(os.getenv("HERMES_AGENT_TIMEOUT", 1800))
```

**你应该怎么配**：保持默认 `1800` 就行。除非你经常跑需要几小时不动的慢任务。

---

### `restart_drain_timeout: 60`

**说人话**：Gateway 重启时，给正在运行的任务 60 秒收尾。

**什么时候用**：如果你发现重启时任务经常被中断，可以调大。

**源码位置**：`gateway/run.py:1424`

---

### `gateway_timeout_warning: 900`

**说人话**：代理空闲 15 分钟时，先发个警告通知，然后再等 15 分钟才真正超时。

**源码位置**：`gateway/run.py:209`

---

### `gateway_notify_interval: 600`

**说人话**：长时间任务中，每 10 分钟发一条"仍在工作中"的通知，让你知道 bot 没死。

**源码位置**：`gateway/run.py:211`

**你应该怎么配**：嫌通知太多可以调大（比如 `1800` = 30 分钟），嫌太少可以调小。

---

### `tool_use_enforcement: "auto"`

**说人话**：强制模型"真的调用工具"而不是"嘴上说我要调用工具"。

- `"auto"` = 只对 GPT/Codex 模型生效
- `true` = 所有模型都强制
- `false` = 不强制
- `["gpt", "qwen"]` = 只对这些模型生效

**源码位置**：`run_agent.py:1620`

---

### `service_tier: ""`

**说人话**：OpenAI 的服务优先级（`"default"` 或 `"priority"`）。付费用户可以选 priority 获得更快响应。

---

## 二、重试相关（你最关心的！）

### ⚠️ 你的 fork 没有这些配置！

你的 fork（`Setsuna-Yukirin/hermes-agent`）**还没有** `api_max_retries` 配置项。重试次数硬编码为 3 次。

**硬编码位置**：`run_agent.py:9293`

```python
max_retries = 3  # ← 写死的！
```

**上游已修复**：PR #14730 添加了 `api_max_retries` 配置，2026-04-23 合并。

详见 [05-issue-11616.md](05-issue-11616.md)。

---

### 退避算法（jittered_backoff）

重试之间的等待时间不是固定的，而是**指数增长 + 随机抖动**：

| 第几次重试 | 基础等待 | 随机抖动 | 实际等待范围 |
|-----------|---------|---------|-------------|
| 第 1 次 | 5 秒 | 0~2.5 秒 | 5~7.5 秒 |
| 第 2 次 | 10 秒 | 0~5 秒 | 10~15 秒 |
| 第 3 次 | 20 秒 | 0~10 秒 | 20~30 秒 |

**为什么用抖动**：防止多个会话同时重试，给 provider 造成"雷击效应"（thundering herd）。

**源码位置**：`agent/retry_utils.py:19`

```python
def jittered_backoff(attempt, *, base_delay=5.0, max_delay=120.0, jitter_ratio=0.5):
    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
    jitter = random.uniform(0, jitter_ratio * delay)
    return delay + jitter
```

---

## 三、`providers` — API 提供商配置

### `request_timeout_seconds`

**说人话**：单次 API 请求的最大等待时间。超过这个时间就认为请求失败。

```yaml
providers:
  deepseek:
    request_timeout_seconds: 300  # 5 分钟超时
```

**源码位置**：`hermes_cli/timeouts.py:14`

```python
def get_provider_request_timeout(provider_id, model=None):
    # 1. 先看模型级别的 timeout_seconds
    # 2. 再看 provider 级别的 request_timeout_seconds
    # 3. 都没有就返回 None（用 SDK 默认值）
```

### `stale_timeout_seconds`

**说人话**：非流式响应的"过时"超时。比 `request_timeout_seconds` 更长，用于判断响应是否已经"凉了"。

---

## 四、`fallback_providers` — 备用提供商

**说人话**：主提供商挂了的时候，自动切换到这些备用选项。

```yaml
fallback_providers:
  - provider: openai
    model: gpt-4o-mini
  - provider: anthropic
    model: claude-sonnet-4-20250514
```

**工作原理**：
1. 主 provider 重试 `max_retries` 次全部失败
2. 取 `fallback_providers` 列表中的第 1 个
3. 替换 `self.client`、`self.model`、`self.provider`
4. 重置 `retry_count = 0`，重新开始重试
5. 如果也失败了，取第 2 个，以此类推

**源码位置**：`run_agent.py:6285` 的 `_try_activate_fallback()` 方法

**关键细节**：
- Fallback 是**按轮次**触发的，不是按会话
- 每次 API 调用失败后都会检查是否需要 fallback
- 切换后 retry_count 重置为 0，意味着又可以重试 3 次

详见 [04-fallback-chain.md](04-fallback-chain.md)。

---

## 五、`terminal` — 终端配置

### `backend: "local"`

**说人话**：命令在哪里执行。

- `"local"` = 在本机执行
- `"docker"` = 在 Docker 容器里执行（更安全）
- `"ssh"` = 在远程服务器执行
- `"modal"` = 在 Modal 云函数上执行

### `timeout: 180`

**说人话**：单个终端命令最多跑 3 分钟。超过就杀掉。

### `persistent_shell: true`

**说人话**：多个命令共享同一个 shell 环境（cd 切换、环境变量都保留）。

---

## 六、`compression` — 上下文压缩

### `threshold: 0.50`

**说人话**：上下文窗口用到 50% 时，触发压缩。

### `target_ratio: 0.20`

**说人话**：压缩后保留到阈值的 20%（即 50% × 20% = 10% 的上下文）。

### `protect_last_n: 20`

**说人话**：至少保留最近 20 条消息不压缩（保持对话连贯性）。

---

## 七、`delegation` — 子代理

### `max_iterations: 50`

**说人话**：每个子代理最多 50 次工具调用。

### `max_concurrent_children: 3`

**说人话**：最多同时跑 3 个子代理。

### `max_spawn_depth: 1`

**说人话**：子代理的嵌套深度。
- `1` = 扁平（主代理 → 子代理）
- `2` = 两层（主代理 → 编排者 → 叶子）
- `3` = 三层

---

## 八、`display` — 显示风格

### `personality: "kawaii"`

**说人话**：界面的"性格"。可选：`kawaii`（可爱）、`technical`（技术）、`concise`（简洁）等。

### `streaming: false`

**说人话**：是否流式显示（一个字一个字蹦出来）。关闭则等全部生成完一次性显示。

### `interim_assistant_messages: true`

**说人话**：Gateway 模式下是否显示中间状态消息（"正在搜索..."、"正在写文件..."）。

---

## 九、`memory` — 记忆系统

### `memory_char_limit: 2200`

**说人话**：持久记忆的字符上限，约 800 个 token。

### `user_char_limit: 1375`

**说人话**：用户档案的字符上限，约 500 个 token。

---

## 十、`approvals` — 危险命令审批

### `mode: "manual"`

**说人话**：
- `"manual"` = 每次危险命令都问你
- `"smart"` = 用辅助 LLM 自动判断低风险放行、高风险问你
- `"off"` = 全部放行（= `--yolo` 模式）

### `cron_mode: "deny"`

**说人话**：Cron 任务（定时任务）遇到危险命令时，默认拒绝。

---

## 十一、`sessions` — 会话管理

### `auto_prune: false`

**说人话**：是否自动删除旧会话。默认关闭（历史对话有价值）。

### `retention_days: 90`

**说人话**：保留 90 天的会话历史。

---

## 十二、其他常用配置

| 配置项 | 默认值 | 说人话 |
|--------|--------|--------|
| `file_read_max_chars` | `100000` | 单次读文件最多 10 万字 |
| `timezone` | `""` | 时区（空 = 服务器本地时间） |
| `network.force_ipv4` | `false` | 强制用 IPv4（IPv6 不通时开启） |
| `logging.level` | `"INFO"` | 日志级别（`DEBUG`/`INFO`/`WARNING`） |
