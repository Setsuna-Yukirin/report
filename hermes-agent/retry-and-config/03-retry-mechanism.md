# 03 — 重试机制源码分析

> 从源代码层面，看 Hermes Agent 的重试逻辑到底是怎么跑的。

---

## 一、重试循环在哪里？

**文件**：`run_agent.py`  
**方法**：`AIAgent.run_conversation()`  
**行号**：约 9290-11200

### 初始化（第 9290-9303 行）

```python
api_start_time = time.time()
retry_count = 0           # 重试计数器，从 0 开始
max_retries = 3           # ← 硬编码！你的 fork 没有配置项
primary_recovery_attempted = False  # 主 provider 恢复尝试标志
max_compression_attempts = 3        # 上下文压缩重试上限
codex_auth_retry_attempted = False
anthropic_auth_retry_attempted = False
nous_auth_retry_attempted = False
```

### 主循环（第 9308 行）

```python
while retry_count < max_retries:
    # 1. 检查 Nous Portal 限速
    # 2. 调用 API
    # 3. 处理响应
    # 4. 如果失败，retry_count += 1，然后 continue 重试
```

---

## 二、什么情况下会触发重试？

### 情况 A：API 返回了响应，但内容无效

**触发条件**（第 9570-9613 行）：
- 响应体为空
- 响应体格式错误（不是合法的 JSON/消息）
- 响应中有 `error` 字段

**处理流程**：

```python
# 第 9570 行附近
if not response or not response.choices:
    retry_count += 1
    
    # 先尝试 fallback
    if self._try_activate_fallback():
        retry_count = 0
        compression_attempts = 0
        primary_recovery_attempted = False
        continue  # 用新的 provider 重新开始
    
    # 没有 fallback？检查是否已到最大重试次数
    if retry_count >= max_retries:
        self._emit_status(f"⚠️ Max retries ({max_retries}) for invalid responses — trying fallback...")
        if self._try_activate_fallback():
            retry_count = 0
            continue
        # 彻底放弃
        self._emit_status(f"❌ Max retries ({max_retries}) exceeded for invalid responses. Giving up.")
        return {"completed": False, "error": "..."}
    
    # 退避等待
    wait_time = jittered_backoff(retry_count, base_delay=5.0, max_delay=120.0)
    self._vprint(f"⏳ Retrying in {wait_time:.1f}s...")
    time.sleep(wait_time)
    continue  # 重试
```

### 情况 B：API 调用抛出异常

**触发条件**（第 10280-11200 行）：
- `APIConnectionError` — 连接失败
- `APITimeoutError` — 请求超时
- `RateLimitError` — 被限速（HTTP 429）
- `InternalServerError` — 服务端 5xx 错误
- 网络断开、连接重置等

**处理流程**：

```python
except Exception as api_error:
    retry_count += 1
    
    # 记录日志
    logger.warning(
        "API call failed (attempt %s/%s) error_type=%s summary=%s",
        retry_count, max_retries, error_type, _error_summary,
    )
    
    # 打印给用户看
    self._vprint(f"⚠️ API call failed (attempt {retry_count}/{max_retries}): {error_type}")
    
    # ── 特殊处理：限速 ──
    if is_rate_limited:
        if self._try_activate_fallback():
            retry_count = 0
            continue
    
    # ── 特殊处理：payload 太大 ──
    if is_payload_too_large:
        retry_count = max_retries  # 跳过重试，直接 fallback
        continue
    
    # ── 特殊处理：非重试错误（4xx） ──
    if is_client_error:
        if self._try_activate_fallback():
            retry_count = 0
            continue
        # 4xx 错误不重试，直接返回
        return {"completed": False, "failed": True}
    
    # ── 到达最大重试次数 ──
    if retry_count >= max_retries:
        # 1. 尝试重建主 provider 连接（一次机会）
        if not primary_recovery_attempted and self._try_recover_primary_transport(api_error, ...):
            primary_recovery_attempted = True
            retry_count = 0
            continue
        
        # 2. 尝试 fallback
        self._emit_status(f"⚠️ Max retries ({max_retries}) exhausted — trying fallback...")
        if self._try_activate_fallback():
            retry_count = 0
            continue
        
        # 3. 彻底放弃
        self._emit_status(f"❌ API failed after {max_retries} retries")
        return {"completed": False, "failed": True}
    
    # ── 退避等待 ──
    wait_time = _retry_after if _retry_after else jittered_backoff(retry_count, base_delay=2.0, max_delay=60.0)
    self._emit_status(f"⏳ Retrying in {wait_time:.1f}s (attempt {retry_count}/{max_retries})...")
    time.sleep(wait_time)
    continue
```

---

## 三、Primary Recovery（主 Provider 恢复）

**文件**：`run_agent.py`  
**方法**：`_try_recover_primary_transport()`  
**行号**：约 6544-6620

### 作用

在重试耗尽后，**再给主 provider 一次机会** — 但这次会重建整个客户端连接（清除连接池）。

### 什么时候触发？

1. `retry_count >= max_retries`（重试已用完）
2. 错误类型是**瞬态传输错误**：
   - `ConnectError`
   - `RemoteProtocolError`
   - `APIConnectionError`
   - `APITimeoutError`
3. 当前**不是** OpenRouter 或 Nous（这些聚合 provider 自己管理连接池）
4. 当前**没有**激活 fallback（`not self._fallback_activated`）

### 做了什么？

```python
def _try_recover_primary_transport(self, api_error, *, retry_count, max_retries):
    # 1. 关闭旧客户端（释放陈旧连接）
    self._close_openai_client(self.client, reason="primary_recovery")
    
    # 2. 从快照重建（用最初的配置）
    rt = self._primary_runtime
    self.client = self._create_openai_client(dict(rt["client_kwargs"]))
    
    # 3. 等几秒再试
    wait_time = min(3 + retry_count, 8)  # 最多等 8 秒
    time.sleep(wait_time)
    
    return True  # 告诉调用者：我帮你恢复了，继续重试吧
```

### 为什么要这样做？

有时候 provider 没挂，只是**连接池里的某个连接断了**（TCP reset、代理超时等）。重建客户端可以拿到新连接，问题就解决了。

---

## 四、退避算法详解

**文件**：`agent/retry_utils.py`  
**函数**：`jittered_backoff()`  
**行号**：19-57

### 公式

```
delay = min(base_delay × 2^(attempt-1), max_delay)
jitter = random.uniform(0, jitter_ratio × delay)
total = delay + jitter
```

### 两种退避场景

| 场景 | base_delay | max_delay | 用途 |
|------|-----------|-----------|------|
| 无效响应 | 5.0s | 120.0s | API 返回了但内容不对 |
| API 异常 | 2.0s | 60.0s | API 调用本身失败了 |

### 实际等待时间

**无效响应场景**：

| 第几次 | 基础 | 抖动范围 | 实际范围 |
|--------|------|---------|---------|
| 1 | 5s | 0~2.5s | 5~7.5s |
| 2 | 10s | 0~5s | 10~15s |
| 3+ | 20s（ capped at 120） | 0~10s | 20~30s |

**API 异常场景**：

| 第几次 | 基础 | 抖动范围 | 实际范围 |
|--------|------|---------|---------|
| 1 | 2s | 0~1s | 2~3s |
| 2 | 4s | 0~2s | 4~6s |
| 3+ | 8s（capped at 60） | 0~4s | 8~12s |

### 为什么用抖动？

假设 10 个会话同时遇到 provider 故障，如果都用固定的 5 秒退避，那 5 秒后 10 个会话**同时**重试，provider 会被瞬间打爆。

加上抖动后，每个会话的等待时间不同，重试分散开来，减轻 provider 压力。

---

## 五、完整流程图

```
用户发消息
    │
    ▼
┌─────────────────────────────────────┐
│  retry_count = 0                    │
│  max_retries = 3 (硬编码)            │
│  while retry_count < max_retries:   │
└─────────────┬───────────────────────┘
              │
              ▼
        调用 API
              │
      ┌───────┴───────┐
      │               │
   成功响应         失败/异常
      │               │
      ▼               ▼
  处理响应      retry_count += 1
                    │
              ┌─────┴─────┐
              │           │
         有 fallback？   无 fallback
              │           │
              ▼           ▼
         切换到      检查是否
         fallback    retry_count >= max_retries
              │      │           │
              ▼      是          否
         retry_count          退避等待
         = 0                  然后重试
         continue
                    │
              ┌─────┴─────┐
              │           │
         已到上限     未到上限
              │           │
              ▼           ▼
         尝试          退避等待
         Primary       然后重试
         Recovery
              │
         ┌────┴────┐
         │         │
      成功       失败
         │         │
         ▼         ▼
     retry_count  尝试
     = 0          fallback
     continue     (如果有)
                    │
              ┌─────┴─────┐
              │           │
         有 fallback   无 fallback
              │           │
              ▼           ▼
         切换并       返回错误
         continue    给用户
```

---

## 六、你的 fork 与上游的差异

### 你的 fork（`Setsuna-Yukirin/hermes-agent`）

```python
# run_agent.py:9293
max_retries = 3  # 硬编码，无法配置
```

### 上游（`NousResearch/hermes-agent`，PR #14730 之后）

```python
# run_agent.py
try:
    _raw_api_retries = _agent_section.get("api_max_retries", 3)
    _api_retries = int(_raw_api_retries)
    if _api_retries < 1:
        _api_retries = 1
except (TypeError, ValueError):
    _api_retries = 3
self._api_max_retries = _api_retries

# 后面用 self._api_max_retries 代替硬编码的 3
```

**差异**：上游多了一个配置项 `agent.api_max_retries`，可以自定义重试次数。
