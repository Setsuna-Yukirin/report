# 04 — Fallback 回退链机制

> 当主 provider 挂了，Hermes 怎么切换到备用 provider？

---

## 一、Fallback 是什么？

Fallback 就是"备胎"。主 provider（比如 DeepSeek）连续失败后，Hermes 会自动切换到配置好的备用 provider（比如 OpenAI），继续完成任务。

**关键特性**：
- Fallback 是**按轮次**触发的，不是按会话
- 每次 API 调用失败后都会检查是否需要 fallback
- 切换后 `retry_count` 重置为 0，意味着又可以重试 3 次
- 可以配置多个 fallback，形成一个**链**

---

## 二、Fallback 链怎么配置？

### 方式 1：在 config.yaml 中配置

```yaml
fallback_providers:
  - provider: openai
    model: gpt-4o-mini
  - provider: anthropic
    model: claude-sonnet-4-20250514
    base_url: https://api.anthropic.com/v1
    api_key: ${ANTHROPIC_API_KEY}
```

### 方式 2：通过 /model 命令临时切换

```bash
/model openai/gpt-4o-mini
```

这会替换当前 provider，但不会添加到 fallback 链中。

---

## 三、Fallback 链在代码中怎么实现的？

### 1. 初始化（`run_agent.py:1276-1299`）

```python
# Provider fallback chain — ordered list of backup providers
# 支持两种格式：
# 1. 新的列表格式 fallback_providers
# 2. 旧的单个字典格式 fallback_model

if isinstance(fallback_model, list):
    self._fallback_chain = [
        f for f in fallback_model
        if isinstance(f, dict) and f.get("provider") and f.get("model")
    ]
elif isinstance(fallback_model, dict) and fallback_model.get("provider"):
    self._fallback_chain = [fallback_model]
else:
    self._fallback_chain = []

self._fallback_index = 0        # 当前 fallback 位置
self._fallback_activated = False # 是否已经激活过 fallback
self._fallback_model = self._fallback_chain[0] if self._fallback_chain else None
```

### 2. 激活 Fallback（`_try_activate_fallback()`，第 6285-6400 行）

这是核心方法，负责实际切换：

```python
def _try_activate_fallback(self) -> bool:
    """Switch to the next fallback model/provider in the chain.
    
     Called when the current model is failing after retries.
    Swaps the OpenAI client, model slug, and provider in-place
    so the retry loop can continue with the new backend.
    """
    # 1. 检查是否已经用完所有 fallback
    if self._fallback_index >= len(self._fallback_chain):
        return False  # 没有更多备胎了
    
    # 2. 取下一个 fallback
    fb = self._fallback_chain[self._fallback_index]
    self._fallback_index += 1
    fb_provider = fb.get("provider").strip().lower()
    fb_model = fb.get("model").strip()
    
    if not fb_provider or not fb_model:
        return self._try_activate_fallback()  # 跳过无效的，试下一个
    
    # 3. 用集中式路由构建新客户端
    fb_client, _resolved_fb_model = resolve_provider_client(
        fb_provider, model=fb_model, raw_codex=True,
        explicit_base_url=fb_base_url_hint,
        explicit_api_key=fb_api_key_hint
    )
    
    if fb_client is None:
        return self._try_activate_fallback()  # 构建失败，试下一个
    
    # 4. 替换当前状态（原地修改！）
    old_model = self.model
    self.model = fb_model
    self.provider = fb_provider
    self.base_url = fb_base_url
    self.api_mode = fb_api_mode  # chat_completions / anthropic_messages / etc.
    self.api_key = effective_key
    
    # 5. 清除传输缓存
    if hasattr(self, "_transport_cache"):
        self._transport_cache.clear()
    
    self._fallback_activated = True
    
    return True  # 切换成功！
```

### 3. 什么时候调用？

在重试循环中，**每次失败后**都会调用：

```python
# 无效响应时
if retry_count >= max_retries:
    if self._try_activate_fallback():
        retry_count = 0
        compression_attempts = 0
        primary_recovery_attempted = False
        continue  # 用新 provider 重新开始

# API 异常时
if retry_count >= max_retries:
    # 先尝试 primary recovery
    if not primary_recovery_attempted and self._try_recover_primary_transport(...):
        ...
    # 再尝试 fallback
    self._emit_status(f"⚠️ Max retries ({max_retries}) exhausted — trying fallback...")
    if self._try_activate_fallback():
        retry_count = 0
        continue
```

---

## 四、Fallback 触发时机详解

### 场景 1：无效响应（API 返回了但内容不对）

```
重试次数 >= max_retries
    │
    ▼
_try_activate_fallback()
    │
    ├─ 成功 → retry_count = 0, continue（重新开始）
    │
    └─ 失败 → 返回错误给用户
```

### 场景 2：API 异常（连接失败、超时等）

```
重试次数 >= max_retries
    │
    ▼
_try_recover_primary_transport()  ← 给主 provider 最后一次机会
    │
    ├─ 成功 → retry_count = 0, continue
    │
    └─ 失败
         │
         ▼
    _try_activate_fallback()
         │
         ├─ 成功 → retry_count = 0, continue
         │
         └─ 失败 → 返回错误给用户
```

### 场景 3：限速（429）

```
检测到限速
    │
    ▼
_try_activate_fallback()  ← 不重试，直接切换！
    │
    ├─ 成功 → retry_count = 0, continue
    │
    └─ 失败 → 返回错误给用户
```

**注意**：限速时**不等待重试耗尽**，立即尝试 fallback。这是为了避免在限速期间继续请求同一个 provider。

---

## 五、Fallback 链的完整流程

假设你配置了：

```yaml
fallback_providers:
  - provider: openai
    model: gpt-4o-mini
  - provider: anthropic
    model: claude-sonnet-4-20250514
  - provider: openrouter
    model: google/gemini-2.5-flash
```

实际运行流程：

```
主 provider: deepseek-v4-flash
    │
    ▼ 失败 3 次（重试耗尽）
    │
    ├─ Primary Recovery（重建连接，再试一次）
    │     │
    │     ▼ 失败
    │     │
    │     ▼
    │  Fallback #1: openai/gpt-4o-mini
    │     │
    │     ▼ 失败 3 次
    │     │
    │     ├─ Primary Recovery（跳过，因为已经激活了 fallback）
    │     │
    │     ▼
    │  Fallback #2: anthropic/claude-sonnet-4
    │     │
    │     ▼ 失败 3 次
    │     │
    │     ▼
    │  Fallback #3: openrouter/google/gemini-2.5-flash
    │     │
    │     ▼ 失败 3 次
    │     │
    │     ▼
    │  所有 fallback 耗尽
    │     │
    │     ▼
    └─ 返回错误给用户
```

---

## 六、Fallback 的状态管理

### 每轮对话重置

每次新的 API 调用（新的对话轮次），fallback 状态**不会重置**：

```python
# _try_activate_fallback() 切换后：
self._fallback_activated = True  # 标记已激活
self._fallback_index = 1         # 已经用了第 1 个
```

这意味着如果 Fallback #1 成功了，后续所有轮次都用 Fallback #1，不会切回主 provider。

### 模型切换时重置

当你用 `/model` 命令切换模型时，fallback 状态会重置：

```python
# run_agent.py:2027-2045
self._fallback_activated = False
self._fallback_index = 0

# 同时清理指向旧主 provider 的 fallback 条目
self._fallback_chain = [
    entry for entry in self._fallback_chain
    if not (entry.get("provider") == old_provider and entry.get("model") == old_model)
]
```

---

## 七、Fallback 与重试的关系

| 维度 | 重试（Retry） | 回退（Fallback） |
|------|-------------|----------------|
| 触发条件 | 每次 API 失败 | 重试耗尽（或限速） |
| 切换目标 | 同一个 provider | 下一个 fallback provider |
| 重置计数器 | 否（retry_count 递增） | 是（retry_count = 0） |
| 等待时间 | 退避算法（2-120s） | 无等待，立即切换 |
| 次数限制 | max_retries（默认 3） | fallback_providers 列表长度 |
| Primary Recovery | 不参与 | 在 fallback 之前尝试一次 |

---

## 八、常见问题

### Q: Fallback 会在什么时候触发？

A: 两种情况：
1. **重试耗尽**：当前 provider 重试 `max_retries` 次全部失败
2. **限速**：收到 429 响应，立即切换（不等重试耗尽）

### Q: Fallback 后还能切回来吗？

A: 不能。一旦激活 fallback，后续所有轮次都用 fallback provider，直到你手动 `/model` 切换或开始新会话。

### Q: 可以配置 fallback 的超时时间吗？

A: 可以。在 fallback provider 配置中指定 `request_timeout_seconds`：

```yaml
fallback_providers:
  - provider: openai
    model: gpt-4o-mini
    base_url: https://api.openai.com/v1
    # 注意：fallback 配置中的超时需要在 providers 中单独配置
```

或者在 `providers` 中配置：

```yaml
providers:
  openai:
    request_timeout_seconds: 120
```

### Q: Fallback 链用完后会怎样？

A: 返回错误给用户，任务结束。不会自动重新开始或切换其他模型。
