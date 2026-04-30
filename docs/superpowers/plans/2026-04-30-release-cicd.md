# Release CI/CD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于旧发布 workflow 构建 PR 打包验证和 tag 触发的本项目 Release 发布流水线，同时保留外部 `dify-plugins` 同步 PR。

**Architecture:** `.github/workflows/package-check.yml` 负责 PR/分支测试和打包验证，上传 `.difypkg` artifact；`.github/workflows/plugin-publish.yml` 作为唯一真实发布入口，负责测试、打包、本仓库 Release asset 上传和外部仓库 PR。`.github/workflows/publish.yml` 保留为手动提示 workflow，避免旧 main push 发布逻辑误触发。

**Tech Stack:** GitHub Actions, GitHub CLI, uv, Python 3.12, Dify plugin CLI.

---

### Task 0: 新增 PR 打包验证

**Files:**
- Create: `.github/workflows/package-check.yml`
- Test: `test/test_release_workflow.py`

- [ ] **Step 1: 添加 workflow 配置测试**

验证 `package-check.yml` 在 PR 和常用开发分支 push 上运行，且先执行 `uv run --no-sync pytest test/` 再执行 Dify 插件打包。

- [ ] **Step 2: 新增 package-check workflow**

配置 Python 3.12、`uv sync --frozen`、完整测试、Dify CLI 下载、插件打包和 artifact 上传。

### Task 1: 更新发布入口

**Files:**
- Modify: `.github/workflows/plugin-publish.yml`
- Modify: `.github/workflows/publish.yml`

- [ ] **Step 1: 将 `plugin-publish.yml` 触发条件改为 tag 和手动触发**

使用 `push.tags: ["*"]` 承接每次 tag 发布，同时保留 `workflow_dispatch` 便于失败后手动重跑。

- [ ] **Step 2: 增加测试门禁**

在打包前安装 Python 3.12、安装 `uv`，运行完整测试：

```bash
uv run --no-sync pytest test/
```

- [ ] **Step 3: 增加版本一致性校验**

从 `manifest.yaml` 读取 `version`，将当前 tag 的 `v` 前缀去掉后比较；不一致则退出。

- [ ] **Step 4: 新增本仓库 Release 发布**

打包完成后使用 `gh release create "$TAG_NAME" --generate-notes` 创建 Release；Release 已存在时允许继续，并使用 `gh release upload "$TAG_NAME" "$PACKAGE_NAME" --clobber` 上传插件包。

- [ ] **Step 5: 保留外部同步 PR**

复用旧逻辑 checkout `${author}/dify-plugins`，复制 `.difypkg`，提交分支，并用 `gh pr create` 创建到 `langgenius/dify-plugins` 的 PR；PR 已存在时只提示。

- [ ] **Step 6: 禁用旧 `publish.yml` 自动发布**

将 `publish.yml` 改成仅 `workflow_dispatch`，运行时输出迁移提示，避免 `main` 推送触发旧发布链路。

### Task 2: 验证

**Files:**
- Test: `.github/workflows/plugin-publish.yml`
- Test: `.github/workflows/publish.yml`

- [ ] **Step 1: YAML 解析校验**

Run: `uv run --no-sync python -c "import pathlib, yaml; [yaml.safe_load(p.read_text()) for p in pathlib.Path('.github/workflows').glob('*.yml')]; print('workflow yaml ok')"`

Expected: 输出 `workflow yaml ok`。

- [ ] **Step 2: 运行测试**

Run:

```bash
uv run --no-sync pytest test/
```

Expected: 全部测试通过。

- [ ] **Step 3: 检查 diff 空白错误**

Run: `git diff --check`

Expected: 无输出，退出码为 0。
