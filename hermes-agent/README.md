# Hermes Agent 记忆系统总体架构

## 文档导航

本研究仓库包含 Hermes Agent 记忆系统的详细分析：

```
hermes-agent/
├── README.md                      # 本文件 - 总体架构和导航
├── memory-system/
│   └── README.md                  # 持久化记忆系统详解
├── skills-system/
│   └── README.md                  # 技能系统详解
├── context-system/
│   └── README.md                  # 上下文系统（待补充）
└── architecture/
    └── README.md                  # 整体架构设计（待补充）
```

---

## 1. Hermes Agent 简介

**Hermes Agent** 是由 [Nous Research](https://nousresearch.com) 开发的自主 AI 代理系统。它的核心特点是：

> "The only agent with a built-in learning loop — it creates skills from experience, improves them during use, nudges itself to persist knowledge, and builds a deepening model of who you are across sessions."

Hermes 不仅仅是一个聊天机器人或代码助手，它是一个**自我改进的自主代理**，能够：
- 从经验中创建技能
- 在使用过程中改进技能
- 主动持久化知识
- 跨会话建立用户模型

---

## 2. 记忆系统概览

Hermes 实现了一个**多层次、多类型**的记忆系统：

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Hermes 记忆系统全景                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐           │
│  │  会话级记忆   │  │  持久化记忆   │  │  程序性记忆   │           │
│  │  Session      │  │  Memory       │  │  Skills       │           │
│  ├───────────────┤  ├───────────────┤  ├───────────────┤           │
│  │ • 完整对话    │  │ • MEMORY.md   │  │ • SKILL.md    │           │
│  │ • SQLite 存储 │  │ • USER.md     │  │ • 支持文件    │           │
│  │ • FTS5 搜索   │  │ • 外部 Provider│  │ • 分类管理   │           │
│  │ • Token 追踪  │  │ • 安全扫描    │  │ • 安全扫描    │           │
│  └───────────────┘  └───────────────┘  └───────────────┘           │
│                                                                     │
│  ┌───────────────┐  ┌───────────────┐                              │
│  │  上下文记忆   │  │  人格记忆     │                              │
│  │  Context      │  │  Personality  │                              │
│  ├───────────────┤  ├───────────────┤                              │
│  │ • 项目文件    │  │ • SOUL.md     │                              │
│  │ • 文档引用    │  │ • 人格设定    │                              │
│  │ • @引用语法  │  │ • 沟通风格    │                              │
│  └───────────────┘  └───────────────┘                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.1 记忆类型对比

| 类型 | 存储位置 | 持久化 | 加载方式 | 用途 |
|------|----------|--------|----------|------|
| **Session** | `~/.hermes/state.db` | ✅ SQLite | 自动 | 完整对话历史 |
| **Memory** | `~/.hermes/memories/` | ✅ 文件 | 自动 | 事实、偏好 |
| **User** | `~/.hermes/memories/` | ✅ 文件 | 自动 | 用户画像 |
| **Skills** | `~/.hermes/skills/` | ✅ 文件 | 按需 | 程序性知识 |
| **Context** | 项目目录 | ✅ 文件 | 按需 | 项目上下文 |
| **Soul** | `~/.hermes/SOUL.md` | ✅ 文件 | 自动 | 人格设定 |

---

## 3. 核心设计原则

### 3.1 分离关注点 (Separation of Concerns)

```
声明性知识 (是什么)          程序性知识 (怎么做)
      ↓                           ↓
┌─────────────┐            ┌─────────────┐
│ MEMORY.md   │            │ SKILL.md    │
│ USER.md     │            │ + 支持文件  │
└─────────────┘            └─────────────┘
      ↓                           ↓
  系统提示注入                按需加载执行
```

### 3.2 冻结快照模式 (Frozen Snapshot)

```
会话开始
    ↓
加载记忆文件 → 捕获冻结快照 → 注入系统提示
    ↓                           ↓
实时状态 (可修改)          稳定状态 (不变)
    ↓                           ↓
工具响应显示               保持 prefix cache
```

**好处**:
- 系统提示稳定，利用 LLM 的 prefix cache
- 避免 mid-session 提示变化导致的混乱
- 工具响应显示最新状态

### 3.3 渐进式披露 (Progressive Disclosure)

```
Level 0: 元数据 (~3k tokens)
    ↓ 用户/代理选择
Level 1: 完整文档 (5-20k tokens)
    ↓ 需要支持文件
Level 2: 特定文件 (可变)
```

**好处**:
- 最小化 token 使用
- 只在需要时加载详细内容
- 支持大量技能库

### 3.4 安全优先 (Security First)

```
写入请求
    ↓
┌─────────────────┐
│ 安全扫描        │
│ • 注入检测      │
│ • 泄露检测      │
│ • 路径遍历      │
│ • 恶意代码      │
└─────────────────┘
    ↓ 通过
原子写入
    ↓
持久化存储
```

---

## 4. 数据流

### 4.1 会话生命周期

```
┌─────────────────────────────────────────────────────────────────┐
│                        会话生命周期                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 初始化                                                       │
│     ├── 创建 SessionDB 连接                                      │
│     ├── 加载 MEMORY.md / USER.md                                │
│     ├── 捕获冻结快照                                            │
│     └── 注入系统提示                                            │
│                                                                 │
│  2. 对话循环                                                     │
│     ├── 接收用户消息                                            │
│     ├── 追加到 messages 表                                       │
│     ├── 调用 LLM (带工具)                                        │
│     ├── 执行工具 (可能修改记忆)                                   │
│     ├── 追加助手响应                                             │
│     └── 更新 token 计数                                          │
│                                                                 │
│  3. 会话结束                                                     │
│     ├── 标记 ended_at                                           │
│     ├── 记录 end_reason                                         │
│     ├── (可选) 提取记忆到 MEMORY.md                              │
│     └── (可选) 创建技能                                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 记忆写入流程

```
用户/代理调用 memory() 工具
    ↓
┌─────────────────────────┐
│ MemoryStore.add()       │
│ • 内容安全扫描          │
│ • 获取文件锁            │
│ • 重新加载磁盘内容      │
│ • 检查字符限制          │
│ • 追加条目              │
│ • 原子写入文件          │
└─────────────────────────┘
    ↓
返回成功/错误
    ↓
工具响应显示实时状态
    ↓
下一个会话使用新快照
```

### 4.3 技能创建流程

```
代理决定创建技能
    ↓
┌─────────────────────────┐
│ skill_manage(create)    │
│ • 验证名称格式          │
│ • 验证 frontmatter      │
│ • 检查名称冲突          │
│ • 创建目录结构          │
│ • 原子写入 SKILL.md     │
└─────────────────────────┘
    ↓
┌─────────────────────────┐
│ 安全扫描 (skills_guard) │
│ • 恶意代码检测          │
│ • 危险命令检测          │
│ • 路径遍历检测          │
└─────────────────────────┘
    ↓ 通过
技能可用
    ↓
┌─────────────────────────┐
│ 失败回滚                │
│ • 删除创建的目录        │
│ • 返回错误详情          │
└─────────────────────────┘
```

---

## 5. 关键技术实现

### 5.1 SQLite 并发控制

```python
# WAL 模式 + 随机抖动重试
class SessionDB:
    _WRITE_MAX_RETRIES = 15
    _WRITE_RETRY_MIN_S = 0.020   # 20ms
    _WRITE_RETRY_MAX_S = 0.150   # 150ms
    
    def _execute_write(self, fn):
        for attempt in range(self._WRITE_MAX_RETRIES):
            try:
                with self._lock:
                    self._conn.execute("BEGIN IMMEDIATE")
                    result = fn(self._conn)
                    self._conn.commit()
                return result
            except sqlite3.OperationalError as exc:
                if "locked" in str(exc):
                    jitter = random.uniform(
                        self._WRITE_RETRY_MIN_S,
                        self._WRITE_RETRY_MAX_S
                    )
                    time.sleep(jitter)  # 随机抖动打破车队效应
```

### 5.2 原子文件写入

```python
def _atomic_write_text(file_path: Path, content: str):
    # 写入临时文件
    fd, temp_path = tempfile.mkstemp(
        dir=str(file_path.parent),
        prefix=f".{file_path.name}.tmp."
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(temp_path, file_path)  # 原子替换
    except Exception:
        os.unlink(temp_path)  # 清理临时文件
        raise
```

### 5.3 文件锁机制

```python
@contextmanager
def _file_lock(path: Path):
    lock_path = path.with_suffix(path.suffix + ".lock")
    fd = open(lock_path, "r+" if msvcrt else "a+")
    try:
        if fcntl:
            fcntl.flock(fd, fcntl.LOCK_EX)  # Unix
        else:
            msvcrt.locking(fd.fileno(), msvcrt.LK_LOCK, 1)  # Windows
        yield
    finally:
        # 释放锁
        fd.close()
```

---

## 6. 扩展机制

### 6.1 外部记忆提供者

```yaml
# ~/.hermes/config.yaml
memory:
  provider: honcho  # 或其他 provider
  
# 支持的 provider:
# - honcho
# - mem0
# - holographic
# - hindsight
# - retaindb
# - byterover
# - supermemory
# - openviking
```

### 6.2 外部技能目录

```yaml
# ~/.hermes/config.yaml
skills:
  external_dirs:
    - /path/to/my/skills
    - /path/to/team/skills
```

### 6.3 平台适配

```yaml
# ~/.hermes/config.yaml
platforms:
  telegram:
    enabled: true
    toolsets: [core, skills, memory, ...]
  discord:
    enabled: true
    toolsets: [core, skills, memory, ...]
```

---

## 7. 监控和调试

### 7.1 查看记忆状态

```bash
# 查看记忆内容
cat ~/.hermes/memories/MEMORY.md
cat ~/.hermes/memories/USER.md

# 查看记忆使用量
# (通过 memory 工具响应查看)
```

### 7.2 查看技能列表

```bash
# CLI
hermes skills list

# 或查看技能目录
ls -la ~/.hermes/skills/
```

### 7.3 查看会话历史

```bash
# SQLite 查询
sqlite3 ~/.hermes/state.db "SELECT * FROM sessions LIMIT 5;"
sqlite3 ~/.hermes/state.db "SELECT * FROM messages WHERE session_id='xxx' LIMIT 10;"
```

---

## 8. 最佳实践总结

### 8.1 记忆使用

| 场景 | 推荐做法 |
|------|----------|
| 用户纠正 | → `memory(action='add', target='user')` |
| 环境发现 | → `memory(action='add', target='memory')` |
| 工作流偏好 | → `memory(action='add', target='user')` |
| 工具 quirks | → `memory(action='add', target='memory')` |
| 任务进度 | → ❌ 不要保存（用 session_search） |
| 临时 TODO | → ❌ 不要保存（用 todo 工具） |

### 8.2 技能创建

| 场景 | 推荐做法 |
|------|----------|
| 复杂任务完成 (5+ 工具) | → `skill_manage(action='create')` |
| 克服棘手错误 | → `skill_manage(action='create')` |
| 发现新工作流 | → `skill_manage(action='create')` |
| 简单一次性任务 | → ❌ 不需要技能 |
| 单工具调用 | → ❌ 不需要技能 |

### 8.3 安全注意事项

- ✅ 始终验证技能名称格式
- ✅ 始终检查路径遍历
- ✅ 始终进行安全扫描
- ✅ 使用原子写入
- ✅ 实现回滚机制
- ❌ 不要信任用户输入
- ❌ 不要跳过安全扫描
- ❌ 不要直接写入敏感文件

---

## 9. 未来研究方向

### 9.1 自动记忆提取

从成功会话轨迹中自动提取记忆条目：

```
会话成功完成
    ↓
分析工具调用序列
    ↓
识别关键决策点
    ↓
生成记忆候选
    ↓
用户确认 → 添加到 MEMORY.md
```

### 9.2 技能自动发现

从重复的成功模式中自动生成技能：

```
检测到相似任务模式 (N 次)
    ↓
提取共同步骤
    ↓
生成 SKILL.md 草稿
    ↓
用户审查 → 创建技能
```

### 9.3 记忆图谱

构建记忆之间的关联网络：

```
MEMORY.md 条目 A ──related_to──→ 条目 B
       │                           │
    used_by                    used_by
       │                           │
       ↓                           ↓
  技能 X  ←──depends_on──→  技能 Y
```

### 9.4 记忆版本控制

```bash
git init ~/.hermes/
git add memories/ skills/
git commit -m "Add new skill: github-pr-workflow"
```

---

## 10. 参考资料

### 10.1 官方文档

- [Hermes Agent 主文档](https://hermes-agent.nousresearch.com/docs/)
- [记忆系统文档](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory)
- [技能系统文档](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills)
- [记忆提供者文档](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory-providers)

### 10.2 源代码

- [`hermes_state.py`](https://github.com/NousResearch/hermes-agent/blob/main/hermes_state.py) - 会话数据库
- [`tools/memory_tool.py`](https://github.com/NousResearch/hermes-agent/blob/main/tools/memory_tool.py) - 记忆工具
- [`tools/skills_tool.py`](https://github.com/NousResearch/hermes-agent/blob/main/tools/skills_tool.py) - 技能工具
- [`tools/skill_manager_tool.py`](https://github.com/NousResearch/hermes-agent/blob/main/tools/skill_manager_tool.py) - 技能管理

### 10.3 相关研究

- Agentskills.io 规范：https://agentskills.io/specification
- Honcho 用户建模：https://app.honcho.dev
- Mem0 记忆管理：https://mem0.ai

---

## 11. 总结

Hermes Agent 的记忆系统是一个精心设计的、多层次的架构，实现了：

1. **完整的会话追踪** (SQLite-backed SessionDB)
2. **持久的声明性记忆** (MEMORY.md / USER.md)
3. **可重用的程序性记忆** (Skills System)
4. **灵活的扩展机制** (外部 Provider 和目录)
5. **严格的安全保障** (扫描、验证、原子写入)

这个系统使 Hermes 能够真正地**从经验中学习**，**适应用户偏好**，并**持续自我改进**。

---

*最后更新：2024 年*
*作者：Hermes Agent 研究团队*
