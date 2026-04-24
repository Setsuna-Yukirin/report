# Hermes Agent 重试机制与配置解析

## 背景

2026-04-25，用户在通过飞书使用 Hermes Agent 时切换到 DeepSeek 模型，遭遇了大量超时和重连报错：

```
⚠️ No response from provider for 300s (model: deepseek-v4-flash, context: ~128,928 tokens). Reconnecting...
⏳ Still working... (10 min elapsed — iteration 1/90, waiting for stream response (270s, no chunks yet))
⚠️ Gateway restarting — Your current task will be interrupted.
```

最终系统重启后会话丢失，回到了默认模型。

## 本报告结构

| 文件 | 内容 |
|------|------|
| [01-overview.md](01-overview.md) | 问题全貌：你遇到了什么、为什么发生 |
| [02-config-reference.md](02-config-reference.md) | 所有配置项的中文解释（说人话版） |
| [03-retry-mechanism.md](03-retry-mechanism.md) | 重试机制的源码级分析 |
| [04-fallback-chain.md](04-fallback-chain.md) | Fallback 回退链是怎么工作的 |
| [05-issue-11616.md](05-issue-11616.md) | GitHub Issue #11616 和 PR #14730 详解 |
| [06-practical-guide.md](06-practical-guide.md) | 实用指南：你应该怎么配 |

## 源码来源

- **Fork 仓库**：`Setsuna-Yukirin/hermes-agent`（位于 `~/.hermes/hermes-agent/hermes-agent/`）
- **上游仓库**：`NousResearch/hermes-agent`
- **分析时的最新提交**：`88b6eb9a chore(release): map Nan93 in AUTHOR_MAP`
- **Issue #11616**：[adjustable provider reconnection attempt count](https://github.com/NousResearch/hermes-agent/issues/11616)（已关闭）
- **PR #14730**：[feat(agent): make API retry count configurable](https://github.com/NousResearch/hermes-agent/pull/14730)（已合并，2026-04-23）

## 核心发现

1. **你的 fork 还没有 `api_max_retries` 配置项** — PR #14730 是昨天（2026-04-23）才合并的
2. **重试次数硬编码为 3 次** — `run_agent.py:9293` 的 `max_retries = 3`
3. **每次重试的退避时间**：5s → 10s → 20s（带随机抖动）
4. **Gateway 超时是"不活跃超时"** — 不是总运行时间，是空闲时间
5. **Fallback 链在重试耗尽后才会触发** — 不是第一次失败就切换
