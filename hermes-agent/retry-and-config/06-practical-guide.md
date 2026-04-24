# 06 — 实用指南：你应该怎么配

> 基于前面的分析，给你一套可以直接抄的配置方案。

---

## 一、快速修复（现在就能用）

### 方案 A：修改源码（临时方案）

编辑 `~/.hermes/hermes-agent/hermes-agent/run_agent.py`：

```python
# 找到第 9293 行
max_retries = 3

# 改成
max_retries = 1  # 只试 1 次就放弃，立刻走 fallback
```

**优点**：立刻生效，不用更新代码  
**缺点**：下次更新 fork 会被覆盖

---

### 方案 B：合并上游修复（推荐）

```bash
cd ~/.hermes/hermes-agent/hermes-agent

# 1. 添加上游仓库
git remote add upstream https://github.com/NousResearch/hermes-agent.git 2>/dev/null || true

# 2. 获取更新
git fetch upstream

# 3. 合并（可能有冲突需要解决）
git merge upstream/main

# 4. 如果冲突了，解决后提交
git add -A
git commit -m "merge upstream: include api_max_retries and other fixes"
```

**优点**：获得所有最新修复和改进  
**缺点**：可能有冲突需要手动解决

---

### 方案 C：Cherry-pick 单个提交（最小改动）

```bash
cd ~/.hermes/hermes-agent/hermes-agent

# 只合并 PR #14730 的改动
git cherry-pick 19a6771ee9fc23f17fb012ae828f40124b9daf78
```

**优点**：只引入一个功能的改动，冲突少  
**缺点**：没有上游的其他修复

---

## 二、推荐配置

### 场景 1：你有多个 API 密钥（最推荐）

```yaml
# ~/.hermes/config.yaml

# 主 provider
model: deepseek-v4-flash
provider: custom
base_url: https://api.deepseek.com/v1

# 备用 provider 链
fallback_providers:
  - provider: openai
    model: gpt-4o-mini
  - provider: anthropic
    model: claude-sonnet-4-20250514

agent:
  api_max_retries: 1        # 只重试 1 次就切换
  max_turns: 90
  gateway_timeout: 1800     # 30 分钟不活跃超时
  gateway_timeout_warning: 900
  gateway_notify_interval: 600
```

**效果**：
- DeepSeek 第 1 次失败 → 立刻切换到 OpenAI
- OpenAI 也挂了 → 切换到 Anthropic
- 全部挂了 → 返回错误

---

### 场景 2：你只有一个 API 密钥

```yaml
# ~/.hermes/config.yaml

model: deepseek-v4-flash
provider: custom
base_url: https://api.deepseek.com/v1

agent:
  api_max_retries: 2        # 给 provider 2 次机会
  max_turns: 90
  gateway_timeout: 1800
  gateway_timeout_warning: 900
  gateway_notify_interval: 600
```

**效果**：
- 第 1 次失败 → 等 5 秒重试
- 第 2 次失败 → 等 10 秒重试
- 第 3 次失败 → 放弃，返回错误

---

### 场景 3：你经常跑长时间任务

```yaml
# ~/.hermes/config.yaml

agent:
  api_max_retries: 1
  max_turns: 200            # 更多迭代次数
  gateway_timeout: 3600     # 1 小时不活跃超时
  gateway_timeout_warning: 1800
  gateway_notify_interval: 300  # 每 5 分钟通知一次

fallback_providers:
  - provider: openai
    model: gpt-4o
```

---

## 三、Provider 超时配置

### 为特定 provider 设置超时

```yaml
providers:
  deepseek:
    request_timeout_seconds: 300  # 5 分钟超时
    models:
      deepseek-v4-flash:
        timeout_seconds: 600      # 这个模型给 10 分钟
      deepseek-v4-pro:
        timeout_seconds: 300
```

### 环境变量覆盖

```bash
# 全局超时（所有 provider）
export HERMES_API_TIMEOUT=600

# 在 ~/.bashrc 或 ~/.hermes/.env 中设置
```

---

## 四、Gateway 超时调优

### 你的当前配置

```yaml
agent:
  gateway_timeout: 1800           # 30 分钟 ✓
  gateway_timeout_warning: 900    # 15 分钟 ✓
  gateway_notify_interval: 600    # 10 分钟 ✓
```

**评价**：已经很合理了，不需要改。

### 什么时候需要调整？

| 情况 | 建议 |
|------|------|
| 经常跑需要几小时的慢任务 | `gateway_timeout: 7200`（2 小时） |
| 嫌通知太多 | `gateway_notify_interval: 1800`（30 分钟） |
| 想更早收到警告 | `gateway_timeout_warning: 600`（10 分钟） |
| 永不超时（不推荐） | `gateway_timeout: 0` |

---

## 五、常见问题解答

### Q: `api_max_retries: 1` 会不会太激进？

A: 取决于你的场景：

| 场景 | 推荐值 |
|------|--------|
| 有 fallback provider | `1`（快速切换） |
| 只有一个 provider | `2-3`（多给几次机会） |
| provider 很不稳定 | `1`（别浪费时间） |
| provider 偶尔抽风 | `3`（默认值） |

### Q: 重试和 fallback 是什么关系？

A: 重试是"同一个 provider 再来几次"，fallback 是"换另一个 provider"。

```
失败 → 重试（同一个） → 再失败 → 重试（同一个） → 再失败 → fallback（换一个）
```

设置 `api_max_retries: 1` = "别重试了，直接换"。

### Q: 为什么我的 fallback 没生效？

A: 检查以下几点：

1. **配置格式是否正确**：
```yaml
fallback_providers:
  - provider: openai    # ← 必须是 provider 名称
    model: gpt-4o-mini  # ← 必须是模型 slug
```

2. **API 密钥是否配置**：
```bash
# ~/.hermes/.env
OPENAI_API_KEY=sk-xxxxx
```

3. **是否真的重试耗尽了**：
   - 默认 `max_retries = 3`
   - 每次失败要等退避时间（5s → 10s → 20s）
   - 设置 `api_max_retries: 1` 可以更快触发

4. **查看日志**：
```bash
hermes logs --level WARNING
# 查找 "Max retries" 和 "trying fallback" 关键字
```

### Q: 怎么测试我的配置？

A: 故意制造一个失败场景：

```bash
# 1. 设置一个无效的 base_url
# ~/.hermes/config.yaml
base_url: https://invalid.example.com/v1

# 2. 启动 Hermes
hermes

# 3. 发一条消息
# 观察日志中的重试和 fallback 行为

# 4. 恢复正常配置
```

### Q: 上下文太大（129K tokens）会不会导致超时？

A: 会。大上下文意味着：
- 请求体更大，传输更慢
- 模型需要更多时间处理
- 某些 provider 对大上下文有限制

**建议**：
- 设置更长的 `request_timeout_seconds`
- 启用上下文压缩（`compression.threshold: 0.50` 已默认开启）
- 用 `/compact` 手动压缩对话历史

---

## 六、配置速查表

| 你想实现 | 配置 |
|----------|------|
| 快速切换 fallback | `agent.api_max_retries: 1` |
| 多给 provider 机会 | `agent.api_max_retries: 3`（默认） |
| 增加单个请求超时 | `providers.xxx.request_timeout_seconds: 600` |
| 增加总运行时间 | `agent.gateway_timeout: 3600` |
| 更早收到警告 | `agent.gateway_timeout_warning: 600` |
| 更频繁的通知 | `agent.gateway_notify_interval: 300` |
| 更多工具调用 | `agent.max_turns: 200` |
| 更多并行子代理 | `delegation.max_concurrent_children: 5` |
| 更深的子代理嵌套 | `delegation.max_spawn_depth: 2` |
| 自动清理旧会话 | `sessions.auto_prune: true` |
| 强制 IPv4 | `network.force_ipv4: true` |

---

## 七、你的最佳配置（基于你的实际情况）

根据你的情况（WSL2 + 飞书 + 经常切换模型 + 遇到 DeepSeek 超时），推荐：

```yaml
# ~/.hermes/config.yaml

# 主模型（按需切换）
model: qwen3.5-plus
provider: custom
base_url: https://coding.dashscope.aliyuncs.com/v1

# 备用 provider
fallback_providers:
  - provider: openai
    model: gpt-4o-mini
  - provider: anthropic
    model: claude-sonnet-4-20250514

agent:
  api_max_retries: 1          # ← 关键！快速切换
  max_turns: 90
  gateway_timeout: 1800
  gateway_timeout_warning: 900
  gateway_notify_interval: 600

# Provider 超时
providers:
  deepseek:
    request_timeout_seconds: 300

# 上下文压缩（默认已开启）
compression:
  enabled: True
  threshold: 0.50
  target_ratio: 0.20
  protect_last_n: 20
```

**效果**：
- 主模型出问题 → 1 次重试后立刻切换
- 大上下文 → 自动压缩
- 长时间任务 → 30 分钟不活跃超时
- 全部挂了 → 明确报错，不无限等待
