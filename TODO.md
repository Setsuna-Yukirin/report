# Report 仓库改造 TODO

> 目标：将纯 Markdown 报告仓库升级为 MkDocs + Material 静态文档站，支持 GitHub Pages 自动部署。

---

## 📋 改造清单

### 1. 环境准备
- [ ] 安装 MkDocs Material：`pip install mkdocs-material`
- [ ] 验证安装：`mkdocs --version`

### 2. 项目初始化
- [ ] 在仓库根目录创建 `mkdocs.yml` 配置文件
- [ ] 创建 `docs/` 目录（MkDocs 默认源目录）
- [ ] 配置主题：Material，中文界面，暗色模式支持
- [ ] 配置导航结构（`nav`）：映射现有 Markdown 文件
- [ ] 配置 Markdown 扩展：代码高亮、提示块、表格等

### 3. 内容迁移
- [ ] 将现有 Markdown 文件软链接或复制到 `docs/` 目录
  - [ ] `hermes-agent/` → `docs/hermes-agent/`
  - [ ] `openai-privacy-filter/` → `docs/openai-privacy-filter/`
  - [ ] `README.md` → `docs/index.md`（首页）
- [ ] 添加自定义 CSS（`docs/stylesheets/extra.css`）
- [ ] 添加 Logo 和 Favicon（`docs/assets/`）

### 4. 本地测试
- [ ] 启动本地服务器：`mkdocs serve`
- [ ] 验证页面渲染：导航、搜索、暗色模式、代码块
- [ ] 修复链接路径问题（相对路径 → MkDocs 兼容路径）
- [ ] 构建静态文件：`mkdocs build`
- [ ] 验证 `site/` 目录输出

### 5. 自动化部署
- [ ] 创建 `.github/workflows/deploy.yml`
  - [ ] 触发条件：push to main + 手动触发
  - [ ] 步骤：checkout → setup python → pip install → mkdocs build → upload pages → deploy
  - [ ] 权限配置：contents: read, pages: write, id-token: write
- [ ] 启用 GitHub Pages 设置（Settings → Pages → GitHub Actions）
- [ ] 测试自动部署流程

### 6. 优化与美化
- [ ] 配置顶部标签导航（`navigation.tabs`）
- [ ] 配置搜索建议和高亮
- [ ] 添加代码复制按钮
- [ ] 配置自定义 404 页面
- [ ] 添加站点统计（可选：Google Analytics 或 Umami）

---

## 🎯 预期效果

- **URL**：`https://setsuna-yukirin.github.io/report/`
- **功能**：
  - 左侧目录树导航
  - 顶部搜索栏
  - 暗色/亮色模式切换
  - 代码块高亮 + 复制
  - 响应式设计（手机/平板/电脑）
- **部署**：推送即自动构建部署，零手动操作

---

## 📅 计划时间

| 阶段 | 预计耗时 | 状态 |
|------|---------|------|
| 环境准备 + 初始化 | 10 分钟 | ⬜ 待开始 |
| 内容迁移 + 配置 | 20 分钟 | ⬜ 待开始 |
| 本地测试 + 修复 | 15 分钟 | ⬜ 待开始 |
| GitHub Actions 部署 | 10 分钟 | ⬜ 待开始 |
| 优化美化 | 15 分钟 | ⬜ 待开始 |
| **总计** | **~70 分钟** | |

---

## 📝 备注

- MkDocs 配置文件：`mkdocs.yml`（根目录）
- 文档源目录：`docs/`
- 构建输出：`site/`（不提交到 Git）
- 部署方式：GitHub Pages（Actions）
- 主题：Material for MkDocs（https://squidfunk.github.io/mkdocs-material/）
