# Hermes Agent 技能系统研究报告

## 概述

技能系统是 Hermes Agent 的**程序性记忆**机制，使代理能够将成功的任务执行方法转化为可重用的知识文档。与声明性的 `MEMORY.md`/`USER.md` 不同，技能是**可操作的、面向流程的**知识。

---

## 1. 技能系统架构

### 1.1 目录结构

```
~/.hermes/skills/                    # 技能主目录（单一事实来源）
│
├── autonomous-ai-agents/            # 分类目录（可选）
│   ├── claude-code/
│   │   └── SKILL.md
│   ├── codex/
│   │   └── SKILL.md
│   └── opencode/
│       └── SKILL.md
│
├── creative/
│   ├── architecture-diagram/
│   │   ├── SKILL.md
│   │   └── templates/
│   │       └── dark-theme.svg
│   ├── ascii-art/
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       └── generate.py
│   └── ...
│
├── devops/
│   ├── webhook-subscriptions/
│   │   └── SKILL.md
│   └── ...
│
├── github/
│   ├── github-auth/
│   │   └── SKILL.md
│   ├── github-pr-workflow/
│   │   ├── SKILL.md
│   │   └── references/
│   │       └── pr-template.md
│   └── ...
│
└── mlops/
    ├── axolotl/
    │   ├── SKILL.md
    │   └── references/
    │       └── config-examples.yaml
    └── ...
```

### 1.2 技能类型

| 类型 | 来源 | 可修改 | 位置 |
|------|------|--------|------|
| **Bundled Skills** | 安装包自带 | ✅ | `~/.hermes/skills/` |
| **Hub Skills** | Hermes Hub 下载 | ✅ | `~/.hermes/skills/` |
| **Agent-Created** | 代理自行创建 | ✅ | `~/.hermes/skills/` |
| **External Skills** | 外部目录配置 | ❌ (只读) | 用户指定路径 |

---

## 2. SKILL.md 格式规范

### 2.1 基本结构

```markdown
---
name: skill-name                      # 必需：技能名称（小写，连字符）
description: 简短描述（用于列表显示）  # 必需：≤1024 字符
category: devops                      # 可选：分类
platforms: [cli, telegram, discord]   # 可选：适用平台
tools_required: [terminal, git]       # 可选：依赖工具
trigger_conditions:                   # 可选：触发条件描述
  - "用户要求创建 GitHub PR"
  - "需要代码审查时"
---

# 技能名称

## 何时使用 (Trigger Conditions)

描述何时应该使用此技能。

## 执行步骤 (Procedure)

1. **第一步**: 详细说明
2. **第二步**: 详细说明
3. ...

## 常见陷阱 (Pitfalls)

- ⚠️ 陷阱 1：说明和避免方法
- ⚠️ 陷阱 2：说明和避免方法

## 验证步骤 (Verification)

如何确认任务正确完成：
- [ ] 检查点 1
- [ ] 检查点 2

## 参考资料 (References)

- [链接 1](url)
- [链接 2](url)
```

### 2.2 完整示例

```markdown
---
name: github-pr-workflow
description: 完整的 GitHub Pull Request 工作流 - 创建分支、提交、推送、创建 PR
category: github
platforms: [cli, telegram, discord]
tools_required: [terminal, github-cli]
---

# GitHub PR 工作流

## 何时使用

- 用户要求创建 Pull Request
- 代码审查完成后需要合并
- 功能开发完成需要集成

## 执行步骤

### 1. 检查当前状态

```bash
git status
git branch
```

### 2. 创建功能分支

```bash
git checkout -b feature/feature-name
```

**命名约定**:
- `feature/xxx` - 新功能
- `fix/xxx` - Bug 修复
- `docs/xxx` - 文档更新
- `refactor/xxx` - 重构

### 3. 提交更改

```bash
git add .
git commit -m "feat: 添加新功能

- 详细说明 1
- 详细说明 2

Closes #123"
```

### 4. 推送到远程

```bash
git push -u origin feature/feature-name
```

### 5. 创建 Pull Request

```bash
gh pr create \
  --title "feat: 新功能描述" \
  --body "## 变更说明
- 变更 1
- 变更 2

## 测试
- [ ] 单元测试通过
- [ ] 集成测试通过

## 截图
（如适用）" \
  --base main
```

## 常见陷阱

- ⚠️ **分支命名**: 不要使用中文或空格，使用连字符
- ⚠️ **提交信息**: 遵循 Conventional Commits 规范
- ⚠️ **PR 描述**: 提供足够的上下文和测试说明
- ⚠️ **基础分支**: 确认 PR 目标是正确的分支（通常是 main）

## 验证步骤

- [ ] 分支已创建并推送到远程
- [ ] PR 已创建且链接正确
- [ ] CI/CD 检查通过
- [ ] 相关 Issue 已关联

## 参考资料

- [GitHub Flow](https://guides.github.com/introduction/flow/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [gh CLI 文档](https://cli.github.com/manual/)
```

---

## 3. 技能工具 API

### 3.1 skills_list()

列出所有可用技能。

```python
# 获取所有技能
skills_list()
# 返回: JSON 字符串
# [{"name": "skill1", "description": "...", "category": "..."}, ...]

# 按分类筛选
skills_list(category="github")
```

**Token 效率**: ~3k tokens（仅名称和描述）

### 3.2 skill_view()

查看技能详细内容。

```python
# 查看完整技能
skill_view(name="github-pr-workflow")
# 返回：完整的 SKILL.md 内容

# 查看特定支持文件
skill_view(
    name="github-pr-workflow",
    file_path="references/pr-template.md"
)
# 返回：指定文件内容
```

### 3.3 skill_manage()

管理技能（创建、编辑、删除）。

```python
# 创建新技能
skill_manage(
    action='create',
    name='my-new-skill',
    content='''---
name: my-new-skill
description: 我的新技能
---

# 技能内容
...''',
    category='devops'
)

# 编辑技能（完整重写）
skill_manage(
    action='edit',
    name='my-skill',
    content='完整的 SKILL.md 新内容'
)

# 补丁式修改（推荐）
skill_manage(
    action='patch',
    name='my-skill',
    old_string='旧文本',
    new_string='新文本',
    replace_all=False  # 只替换第一个匹配
)

# 添加支持文件
skill_manage(
    action='write_file',
    name='my-skill',
    file_path='references/config.yaml',
    file_content='''key: value
nested:
  key2: value2'''
)

# 删除支持文件
skill_manage(
    action='remove_file',
    name='my-skill',
    file_path='references/old.md'
)

# 删除整个技能
skill_manage(
    action='delete',
    name='my-skill'
)
```

---

## 4. 技能创建最佳实践

### 4.1 何时创建技能

✅ **应该创建技能**:
- 复杂任务成功完成（5+ 工具调用）
- 克服了棘手错误，发现了 workaround
- 用户明确要求"记住这个方法"
- 发现了非平凡的、可重复的工作流
- 需要跨会话复用的专业知识

❌ **不需要技能**:
- 简单的一次性任务
- 机械性多步骤工作（无推理需求）
- 单个工具调用即可完成
- 已有技能覆盖的场景

### 4.2 技能设计原则

#### 4.2.1 单一职责

每个技能应该专注于一个特定类型的任务：

```
✅ 好：github-pr-workflow（专门处理 PR 创建）
❌ 坏：github-everything（试图处理所有 GitHub 操作）
```

#### 4.2.2 可组合性

技能应该能够组合使用：

```
github-auth → github-pr-workflow → github-code-review
```

#### 4.2.3 参数化

在技能中留出可调整的参数：

```markdown
### 配置参数

- `MAX_ITERATIONS`: 最大迭代次数（默认：50）
- `TIMEOUT`: 超时时间（默认：180 秒）
- `GPU_MODEL`: GPU 型号（默认：RTX 3080）
```

#### 4.2.4 包含验证步骤

每个技能应该有明确的验证清单：

```markdown
## 验证步骤

- [ ] 检查点 1
- [ ] 检查点 2
- [ ] 检查点 3
```

### 4.3 技能命名规范

```
✅ 有效名称:
- github-pr-workflow
- ascii-art
- fine-tuning-with-trl
- rl-chapter-implementation

❌ 无效名称:
- GitHub PR Workflow（包含空格和大写）
- my skill（包含空格）
- 技能名称（包含中文）
```

**规则**:
- 小写字母
- 数字
- 连字符 `-`
- 点 `.`
- 下划线 `_`
- 必须以字母或数字开头
- 最大 64 字符

---

## 5. 技能安全系统

### 5.1 安全扫描 (skills_guard.py)

所有技能（尤其是 agent-created 和 hub-installed）都会经过安全扫描：

```python
# 扫描检查项
scan_skill(skill_dir, source="agent-created")

# 检查内容:
1. 恶意代码注入
2. 危险系统命令（rm -rf, curl | bash 等）
3. 提示注入模式
4. 路径遍历攻击
5. 敏感文件访问（~/.hermes/.env 等）
6. 网络请求（可能泄露数据）
```

### 5.2 安全 verdict

```python
result = scan_skill(...)
allowed, reason = should_allow_install(result)

# Verdict:
# - True: 安全，允许安装
# - False: 危险，阻止安装
# - None: "ask" - 有可疑发现，需要用户确认
```

### 5.3 路径安全

技能文件操作有严格的路径限制：

```python
ALLOWED_SUBDIRS = {"references", "templates", "scripts", "assets"}

# 禁止路径遍历
validate_within_dir(target, skill_dir)
# 检测 "../" 等遍历模式
```

---

## 6. 技能加载机制

### 6.1 渐进式披露

```
┌─────────────────────────────────────────┐
│  Level 0: skills_list()                 │
│  • 仅加载元数据（名称、描述、分类）       │
│  • Token 消耗：~3k                       │
│  • 用途：技能发现和选择                  │
└─────────────────────────────────────────┘
                    ↓ (用户/代理选择技能)
┌─────────────────────────────────────────┐
│  Level 1: skill_view(name)              │
│  • 加载完整 SKILL.md                     │
│  • Token 消耗：可变（通常 5-20k）        │
│  • 用途：执行技能指令                    │
└─────────────────────────────────────────┘
                    ↓ (需要支持文件)
┌─────────────────────────────────────────┐
│  Level 2: skill_view(name, file_path)   │
│  • 加载特定支持文件                      │
│  • Token 消耗：可变                      │
│  • 用途：访问模板、脚本、参考文档        │
└─────────────────────────────────────────┘
```

### 6.2 技能注入方式

技能内容通过以下方式注入到对话中：

1. **Slash 命令**: `/skill-name` 直接加载技能
2. **自然语言**: "使用 github-pr-workflow 技能"
3. **自动触发**: 检测到匹配的场景时

### 6.3 技能缓存

```python
# 技能加载后缓存在内存中
# 避免重复磁盘读取
_cached_skills: Dict[str, str] = {}

def skill_view(name):
    if name in _cached_skills:
        return _cached_skills[name]
    # 从磁盘加载...
```

---

## 7. 外部技能目录

### 7.1 配置方式

```yaml
# ~/.hermes/config.yaml
skills:
  external_dirs:
    - /path/to/my/skills
    - /path/to/team/skills
```

### 7.2 加载优先级

```
1. 本地技能目录 (~/.hermes/skills/) - 最高优先级
2. 外部目录 1
3. 外部目录 2
4. ...
```

### 7.3 只读限制

外部目录中的技能对代理是**只读**的：

```python
def _is_local_skill(skill_path: Path) -> bool:
    """检查技能是否在本地目录（可写）"""
    try:
        skill_path.resolve().relative_to(SKILLS_DIR.resolve())
        return True
    except ValueError:
        return False  # 外部目录，只读
```

---

## 8. 技能与记忆的区别

| 特性 | Memory (MEMORY.md) | Skills (SKILL.md) |
|------|-------------------|-------------------|
| **知识类型** | 声明性（是什么） | 程序性（怎么做） |
| **内容** | 事实、偏好、环境信息 | 流程、方法、最佳实践 |
| **结构** | 简单条目（§分隔） | 完整文档（YAML frontmatter + Markdown） |
| **大小限制** | 2,200 / 1,375 字符 | 100,000 字符 |
| **加载方式** | 始终加载到系统提示 | 按需加载（渐进式） |
| **更新频率** | 高频（每次发现） | 低频（完成任务后） |
| **支持文件** | 无 | 有（references/templates/scripts/assets） |
| **安全扫描** | 基础（注入/泄露） | 完整（代码/命令/路径） |

---

## 9. 实际案例

### 9.1 案例：Harness Engineer 工作流

**背景**: 用户需要遵循特定的 RL 项目开发流程。

**技能内容**:
```markdown
---
name: harness-engineer-workflow
description: Harness Engineer 工作流 - RL/ML 项目专业开发流程
category: software-development
---

# Harness Engineer 工作流

## 何时使用

- 开发新的 RL 功能或模块
- 用户明确要求遵循 Harness Engineer 流程
- 开始新的 RL 教程章节实现

## 工作流程

### 1. 架构文档先行

```bash
# 确认 docs/ 目录存在
ls docs/

# 读取架构书
read_file docs/architecture.md
```

### 2. 制定计划

```python
# 使用 plan 工具
todo(merge=False, todos=[
    {"id": "1", "content": "读取架构书", "status": "pending"},
    {"id": "2", "content": "编写测试", "status": "pending"},
    {"id": "3", "content": "实现功能", "status": "pending"},
    {"id": "4", "content": "运行测试", "status": "pending"},
    {"id": "5", "content": "代码审查", "status": "pending"},
    {"id": "6", "content": "提交推送", "status": "pending"}
])
```

### 3. 测试先行

```python
# 先写单元测试
write_file(
    path="tests/test_feature.py",
    content='''def test_new_feature():
    assert new_feature() == expected_result
'''
)

# 运行测试（应该失败）
terminal(command="pytest tests/test_feature.py")
```

### 4. 实现功能

```python
# 实现代码使测试通过
write_file(
    path="src/feature.py",
    content='''def new_feature():
    return expected_result
'''
)
```

### 5. 代码质量

```bash
# 格式化
black src/feature.py

# Lint
pylint src/feature.py
```

### 6. 提交推送

```bash
git add .
git commit -m "feat: 添加新功能"
git push
```

## 配置参数

- `GPU_MODEL`: RTX 3080（支持快速验证模式）
- `TEST_COVERAGE`: 目标 80%+
- `MAX_ITERATIONS`: 50

## 常见陷阱

- ⚠️ 不要跳过架构书阅读步骤
- ⚠️ 不要跳过测试先行
- ⚠️ 不要忘记代码质量检查
- ⚠️ 不要忘记 git commit push

## 验证步骤

- [ ] 架构书已阅读并理解
- [ ] todo 列表已创建
- [ ] 单元测试已编写并通过
- [ ] 代码已格式化 (black)
- [ ] 代码已通过 lint (pylint)
- [ ] 已 git commit 并 push
```

### 9.2 案例：RL 教程章节实现

```markdown
---
name: rl-chapter-implementation
description: 强化学习教程章节实现工作流
category: software-development
---

# RL 教程章节实现

## 工作流程

1. 阅读章节要求
2. 创建环境类
3. 实现算法
4. 编写测试
5. 运行实验
6. 记录结果

## 环境类模板

```python
class RLGameEnv(gym.Env):
    def __init__(self, config=None):
        super().__init__()
        self.config = config or {}
        # 可调参数
        self.max_steps = self.config.get('max_steps', 1000)
        
    def reset(self):
        # 重置环境状态
        pass
        
    def step(self, action):
        # 执行动作，返回 (observation, reward, done, info)
        pass
```
```

---

## 10. 技能系统总结

### 10.1 核心优势

1. **可重用性**: 一次学习，多次复用
2. **可组合性**: 技能可以组合使用
3. **可扩展性**: 代理可以自行创建新技能
4. **安全性**: 完整的安全扫描机制
5. **Token 效率**: 渐进式披露最小化消耗

### 10.2 与其他记忆系统的协同

```
Session (会话历史)
    ↓ (发现成功模式)
Memory (记录事实)
    ↓ (积累足够经验)
Skills (形成程序性知识)
    ↓ (技能指导未来会话)
Session (更好的表现)
```

### 10.3 未来发展方向

- 技能自动发现（从成功轨迹中提取）
- 技能版本控制
- 技能依赖管理
- 技能性能指标追踪
- 技能共享和协作

---

## 附录：关键文件清单

| 文件 | 作用 |
|------|------|
| `tools/skills_tool.py` | 技能浏览工具（skills_list, skill_view） |
| `tools/skill_manager_tool.py` | 技能管理工具（create/edit/patch/delete） |
| `tools/skills_guard.py` | 技能安全扫描 |
| `agent/skill_utils.py` | 技能加载工具 |
| `hermes_cli/skills_hub.py` | CLI 技能中心命令 |
| `hermes_cli/skills_config.py` | CLI 技能配置命令 |
