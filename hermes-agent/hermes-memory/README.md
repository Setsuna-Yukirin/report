# Hermes Agent 记忆系统研究报告

## 概述

Hermes Agent 实现了一个**多层次、多类型的记忆系统**，使其能够跨会话持久化知识、学习用户偏好、并积累程序性技能。这是 Hermes 作为"自我改进 AI 代理"的核心机制。

---

## 记忆系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Hermes 记忆系统架构                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  会话级记忆     │  │  持久化记忆     │  │  程序性记忆     │ │
│  │  (Session)      │  │  (Memory)       │  │  (Skills)       │ │
│  ├─────────────────┤  ├─────────────────┤  ├─────────────────┤ │
│  │ • SQLite 数据库 │  │ • MEMORY.md     │  │ • SKILL.md      │ │
│  │ • 完整对话历史  │  │ • USER.md       │  │ • references/   │ │
│  │ • Token 统计    │  │ • 外部 Provider │  │ • templates/    │ │
│  │ • FTS5 搜索     │  │   - Honcho      │  │ • scripts/      │ │
│  │                 │  │   - Mem0        │  │ • assets/       │ │
│  │                 │  │   - Holographic │  │                 │ │
│  │                 │  │   - 等 8 种      │  │                 │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐                      │
│  │  上下文记忆     │  │  人格记忆       │                      │
│  │  (Context)      │  │  (Personality)  │                      │
│  ├─────────────────┤  ├─────────────────┤                      │
│  │ • .hermes/      │  │ • SOUL.md       │                      │
│  │ • 项目文档      │  │ • 人格设定      │                      │
│  │ • 参考资料      │  │ • 沟通风格      │                      │
│  └─────────────────┘  └─────────────────┘                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. 会话级记忆 (Session Memory)

### 1.1 SessionDB - SQLite 状态存储

**文件位置**: `hermes_state.py`

**核心设计**:
- 使用 SQLite 数据库 (`~/.hermes/state.db`) 存储所有会话数据
- WAL (Write-Ahead Logging) 模式支持并发读写
- FTS5 全文搜索索引支持快速检索

**数据表结构**:

```sql
-- 会话元数据表
sessions (
    id TEXT PRIMARY KEY,
    source TEXT,              -- 'cli', 'telegram', 'discord' 等
    user_id TEXT,
    model TEXT,
    system_prompt TEXT,
    parent_session_id TEXT,   -- 支持会话链（压缩/子代理）
    started_at REAL,
    ended_at REAL,
    end_reason TEXT,
    message_count INTEGER,
    tool_call_count INTEGER,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cache_read_tokens INTEGER,
    cache_write_tokens INTEGER,
    reasoning_tokens INTEGER,
    estimated_cost_usd REAL,
    actual_cost_usd REAL,
    title TEXT                -- 会话标题（唯一）
)

-- 消息历史表
messages (
    id INTEGER PRIMARY KEY,
    session_id TEXT,
    role TEXT,                -- 'user', 'assistant', 'tool'
    content TEXT,
    tool_call_id TEXT,
    tool_calls TEXT,
    tool_name TEXT,
    timestamp REAL,
    token_count INTEGER,
    finish_reason TEXT,
    reasoning TEXT,           -- 推理过程（思维链）
    reasoning_details TEXT
)

-- FTS5 全文搜索虚拟表
messages_fts (content)
```

**关键特性**:

1. **线程安全的写入机制**:
   - 使用 `BEGIN IMMEDIATE` 提前获取写锁
   - 随机抖动重试 (20-150ms) 避免写冲突"车队效应"
   - 每 50 次写入执行一次 PASSIVE WAL 检查点

2. **会话链支持**:
   - `parent_session_id` 字段支持会话继承
   - 用于上下文压缩、子代理运行等场景

3. **完整的 Token 和成本追踪**:
   - 区分输入/输出/缓存/推理 token
   - 支持多 provider 成本计算

### 1.2 会话生命周期

```python
# 创建会话
db.create_session(
    session_id="abc123",
    source="telegram",
    model="anthropic/claude-opus-4",
    user_id="user_456"
)

# 追加消息
db.append_message(
    session_id="abc123",
    role="user",
    content="你好，帮我写个脚本",
    timestamp=time.time()
)

# 更新 token 计数
db.update_token_counts(
    session_id="abc123",
    input_tokens=1500,
    output_tokens=800,
    estimated_cost_usd=0.012
)

# 结束会话
db.end_session(session_id="abc123", end_reason="max_iterations")
```

---

## 2. 持久化记忆 (Persistent Memory)

### 2.1 核心记忆文件

**文件位置**: `tools/memory_tool.py`

Hermes 有两种核心记忆文件，均位于 `~/.hermes/memories/`:

| 文件 | 用途 | 字符限制 |
|------|------|----------|
| `MEMORY.md` | 代理的个人笔记（环境事实、项目约定、工具特性） | 2,200 字符 |
| `USER.md` | 用户画像（偏好、沟通风格、工作流习惯） | 1,375 字符 |

**条目格式**:
```markdown
══════════════════════════════════════════════
MEMORY (your personal notes) [31% — 684/2,200 chars]
══════════════════════════════════════════════
用户环境：WSL2 (Ubuntu 22.04.5 LTS) 运行在 Windows 上。
§
Hermes Agent 官方文档：https://hermes-agent.nousresearch.com/docs/
§
用户偏好：回答 Hermes Agent 相关问题时，先查阅官方文档确认信息。
```

**条目分隔符**: `§` (Section Sign)

### 2.2 记忆操作 API

```python
# 添加记忆
memory(action='add', target='memory', 
       content='用户偏好使用中文交流。')

# 替换记忆（通过唯一子串匹配）
memory(action='replace', target='user',
       old_text='旧的工作流偏好',
       new_text='新的工作流偏好：测试先行开发')

# 删除记忆
memory(action='remove', target='memory',
       old_text='已过时的环境配置')
```

### 2.3 冻结快照模式 (Frozen Snapshot)

**关键设计决策**:
- 会话开始时，记忆内容被**冻结**为系统提示的一部分
- 会话中的写入**不会**改变当前会话的系统提示
- 新记忆在**下一个会话**才生效

**好处**:
- 保持系统提示稳定，利用 LLM 的 prefix cache
- 避免 mid-session 提示变化导致的上下文混乱
- 工具响应显示实时状态，用户可见最新记忆

```python
class MemoryStore:
    def __init__(self):
        self._system_prompt_snapshot = {"memory": "", "user": ""}
        self.memory_entries = []  # 实时状态
    
    def load_from_disk(self):
        # 加载磁盘内容
        self.memory_entries = self._read_file("MEMORY.md")
        # 捕获冻结快照（用于系统提示）
        self._system_prompt_snapshot = {
            "memory": self._render_block("memory", self.memory_entries),
            "user": self._render_block("user", self.user_entries),
        }
    
    def format_for_system_prompt(self, target):
        # 返回冻结快照，不是实时状态
        return self._system_prompt_snapshot.get(target)
```

### 2.4 安全扫描

记忆内容在写入前会经过安全扫描，防止提示注入和数据泄露：

```python
_MEMORY_THREAT_PATTERNS = [
    (r'ignore\s+(previous|all|above)\s+instructions', "prompt_injection"),
    (r'you\s+are\s+now\s+', "role_hijack"),
    (r'curl\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET)', "exfil_curl"),
    (r'\$HOME/\.hermes/\.env', "hermes_env"),
    # ... 更多模式
]
```

### 2.5 外部记忆提供者 (Memory Providers)

Hermes 支持 8 种外部记忆提供者插件，与内置记忆系统并行工作：

| Provider | 特点 | 适用场景 |
|----------|------|----------|
| **Honcho** | AI 原生跨会话用户建模，语义搜索 | 多代理系统 |
| **Mem0** | 轻量级记忆管理 | 通用场景 |
| **Holographic** | 全息记忆存储 | 复杂知识网络 |
| **Hindsight** | 事后记忆提取 | 经验总结 |
| **RetainDB** | 关系型记忆数据库 | 结构化知识 |
| **Byterover** | 字节级记忆存储 | 高效压缩 |
| **Supermemory** | 超级记忆能力 | 大规模知识 |
| **OpenViking** | 开源维京记忆 | 社区驱动 |

**配置方式**:
```yaml
# ~/.hermes/config.yaml
memory:
  provider: honcho  # 或其他 provider
```

**工作流程**:
1. 每个对话轮次前，预取相关记忆（后台非阻塞）
2. 每轮对话后，同步到外部提供者
3. 会话结束时，提取记忆（如果支持）
4. 内置记忆写入时，镜像到外部提供者

---

## 3. 程序性记忆 (Skills System)

### 3.1 技能系统架构

**文件位置**: `tools/skills_tool.py`, `tools/skill_manager_tool.py`

Skills 是 Hermes 的**程序性记忆**——可重用的任务执行方法。

**目录结构**:
```
~/.hermes/skills/
├── my-skill/
│   ├── SKILL.md           # 主要指令文档（必需）
│   ├── references/        # 参考资料
│   ├── templates/         # 模板文件
│   ├── scripts/           # Python/Shell 脚本
│   └── assets/            # 其他资源
└── category-name/
    └── another-skill/
        └── SKILL.md
```

### 3.2 SKILL.md 格式

```markdown
---
name: skill-name
description: 简短描述（用于技能列表）
category: 可选分类
platforms: [cli, telegram, discord]  # 适用平台
---

# 技能名称

## 触发条件
何时使用此技能

## 执行步骤
1. 第一步
2. 第二步
3. ...

## 常见陷阱
- 陷阱 1
- 陷阱 2

## 验证步骤
如何确认任务完成
```

### 3.3 渐进式披露 (Progressive Disclosure)

技能使用三级加载模式以最小化 token 使用：

```
Level 0: skills_list() 
  → [{name, description, category}, ...] (~3k tokens)

Level 1: skill_view(name) 
  → 完整 SKILL.md 内容 + 元数据

Level 2: skill_view(name, file_path='references/api.md')
  → 特定支持文件
```

### 3.4 技能管理工具

```python
# 创建技能
skill_manage(
    action='create',
    name='my-new-skill',
    content='---\nname: my-new-skill\n...',
    category='devops'
)

# 编辑技能（完整重写）
skill_manage(
    action='edit',
    name='my-skill',
    content='完整的 SKILL.md 新内容'
)

# 补丁式修改
skill_manage(
    action='patch',
    name='my-skill',
    old_string='旧文本',
    new_string='新文本'
)

# 添加支持文件
skill_manage(
    action='write_file',
    name='my-skill',
    file_path='references/config.yaml',
    file_content='key: value'
)

# 删除支持文件
skill_manage(
    action='remove_file',
    name='my-skill',
    file_path='references/old.md'
)

# 删除技能
skill_manage(
    action='delete',
    name='my-skill'
)
```

### 3.5 安全扫描

技能创建和修改时会经过安全扫描（`skills_guard.py`）：

- 检测恶意代码注入
- 检测危险系统命令
- 检测提示注入模式
- 检测路径遍历攻击

---

## 4. 上下文记忆 (Context Memory)

### 4.1 上下文文件

Hermes 自动加载工作区中的上下文文件：

```
.project/
├── .hermes/
│   ├── context.md         # 项目特定上下文
│   └── preferences.yaml   # 项目偏好
├── docs/
│   └── architecture.md    # 架构文档
└── README.md
```

### 4.2 上下文引用

在对话中引用外部文件：

```
@file:path/to/file.py
@docs:architecture.md
```

---

## 5. 人格记忆 (Personality Memory)

### 5.1 SOUL.md

**文件位置**: `~/.hermes/SOUL.md`

定义代理的人格、沟通风格、价值观：

```markdown
# Hermes Agent Personality

## 沟通风格
- 温暖、专业、乐于助人
- 使用表情符号增强亲和力
- 技术解释深入但易懂

## 价值观
- 用户隐私优先
- 主动学习用户偏好
- 持续自我改进

## 特殊行为
- 复杂任务后主动提供技能保存
- 发现环境特性时记录到记忆
```

---

## 6. 记忆系统对比

| 类型 | 持久化 | 作用范围 | Token 效率 | 更新频率 |
|------|--------|----------|------------|----------|
| **Session** | 是 (SQLite) | 单会话 | 高（完整历史） | 实时 |
| **Memory.md** | 是 (文件) | 跨会话 | 极高（精选） | 按需 |
| **User.md** | 是 (文件) | 跨会话 | 极高（精选） | 按需 |
| **Skills** | 是 (文件) | 跨会话 | 高（按需加载） | 按需 |
| **Context** | 是 (文件) | 项目级 | 中 | 手动 |
| **Soul** | 是 (文件) | 全局 | 高 | 罕见 |

---

## 7. 设计亮点

### 7.1 分离关注点

- **声明性记忆** (MEMORY.md/USER.md): "是什么" - 事实、偏好
- **程序性记忆** (Skills): "怎么做" - 流程、方法
- **临时记忆** (Session): "这次对话" - 完整历史

### 7.2 冻结快照模式

会话开始时冻结记忆状态，避免 mid-session 提示变化，保持 prefix cache 稳定。

### 7.3 渐进式披露

技能系统只在需要时加载完整内容，最小化 token 使用。

### 7.4 安全优先

- 记忆内容安全扫描（防注入/防泄露）
- 技能安全扫描（防恶意代码）
- 路径遍历防护
- 原子写入（防损坏）

### 7.5 可扩展性

- 外部记忆提供者插件系统
- 外部技能目录支持
- 多平台适配（CLI/Telegram/Discord 等）

---

## 8. 最佳实践

### 8.1 何时使用记忆 (Memory)

✅ **应该保存**:
- 用户纠正或说"记住这个"
- 用户分享的偏好、习惯、个人细节
- 环境发现（OS、工具、项目结构）
- 工具 quirks、API 特性
- 跨会话有用的稳定事实

❌ **不应该保存**:
- 任务进度
- 会话结果
- 临时 TODO 状态
- 容易重新发现的信息
- 原始数据转储

### 8.2 何时创建技能 (Skill)

✅ **应该创建技能**:
- 复杂任务成功完成（5+ 工具调用）
- 克服了棘手错误
- 发现了非平凡的工作流
- 用户要求"记住这个方法"

❌ **不需要技能**:
- 简单一次性任务
- 机械性多步骤工作（无推理）
- 单个工具调用

---

## 9. 总结

Hermes Agent 的记忆系统是一个**多层次、多类型、安全且可扩展**的设计：

1. **会话级**: 完整的 SQLite -backed 对话历史
2. **持久化**: 精选的 MEMORY.md/USER.md + 外部提供者
3. **程序性**: 可重用的 Skills 系统
4. **上下文**: 项目级文件和引用
5. **人格**: SOUL.md 定义的行为模式

这种设计使 Hermes 能够：
- ✅ 跨会话持续学习
- ✅ 适应用户偏好
- ✅ 积累专业知识
- ✅ 自我改进能力

---

## 附录：关键文件清单

| 文件 | 作用 |
|------|------|
| `hermes_state.py` | SQLite 会话数据库 |
| `tools/memory_tool.py` | 持久化记忆工具 |
| `tools/skills_tool.py` | 技能浏览工具 |
| `tools/skill_manager_tool.py` | 技能管理工具 |
| `tools/registry.py` | 工具注册表 |
| `agent/skill_utils.py` | 技能加载工具 |
| `tools/skills_guard.py` | 技能安全扫描 |
