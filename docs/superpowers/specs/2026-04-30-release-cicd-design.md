# Release CI/CD Design

## 背景

当前仓库已有两个发布相关 workflow：`.github/workflows/publish.yml` 在 `main` 推送时打包并向外部 `dify-plugins` 仓库创建 PR，`.github/workflows/plugin-publish.yml` 在 GitHub Release 发布后执行相似流程。两者包含可复用的 Dify 插件 CLI 下载、`manifest.yaml` 元数据读取、`.difypkg` 打包和外部仓库同步逻辑。

## 目标

- 每个 PR 自动运行测试和插件打包验证。
- 每次推送版本 tag 时自动触发发布流水线。
- 沿用旧 workflow 的 Dify 插件打包流程，生成 `schemarag-<version>.difypkg`。
- 在本项目 GitHub Release 中汇总 release note，并上传 `.difypkg` 供用户直接下载。
- 保留旧的外部 `dify-plugins` 同步 PR 能力，避免破坏已有发布路径。
- 避免两个 workflow 对同一 tag 重复打包、重复发 Release 或重复推外部 PR。

## 设计

新增 `package-check.yml` 作为 PR 打包验证入口，在 `pull_request` 和常用开发分支推送时运行完整测试、Dify CLI 打包，并上传 `.difypkg` artifact 供检查。该 workflow 不创建 Release、不同步外部插件仓库。

保留 `plugin-publish.yml` 作为唯一正式发布入口，并将触发条件改为任意 tag 推送与手动 `workflow_dispatch`。该 workflow 在同一个 job 中完成测试、打包、本仓库 Release 发布、外部仓库同步 PR。

`publish.yml` 不再作为实际发布入口，改为说明性禁用 workflow，仅保留手动触发提示，防止旧的 `main` 推送逻辑误触发。

发布 job 使用最小权限：

- `contents: write` 用于创建/更新本仓库 Release 并上传 asset。
- 外部 `dify-plugins` PR 继续使用现有 `PLUGIN_ACTION` secret。

## 流程

### PR 打包验证

1. Checkout PR 或分支代码。
2. 安装 Python 3.12 和 `uv`。
3. 运行完整测试命令 `uv run --no-sync pytest test/`。
4. 下载 Dify plugin CLI。
5. 从 `manifest.yaml` 读取 `name` 和 `version`。
6. 打包生成 `<name>-<version>.difypkg`。
7. 上传 `.difypkg` 为 GitHub Actions artifact。

### Tag 正式发布

1. Checkout tag 对应代码。
2. 安装 Python 3.12 和 `uv`。
3. 运行完整测试命令 `uv run --no-sync pytest test/`。
4. 下载 Dify plugin CLI。
5. 从 `manifest.yaml` 读取 `name`、`version`、`author`。
6. 校验 tag 版本和 `manifest.yaml` 版本一致，例如 `v0.1.8` 或 `0.1.8` 对应 `0.1.8`。
7. 打包生成 `<name>-<version>.difypkg`。
8. 使用 `gh release create --generate-notes` 创建本仓库 Release；如果 Release 已存在，则更新 notes 并继续上传资产。
9. 使用 `gh release upload --clobber` 上传 `.difypkg`。
10. 沿用旧逻辑 checkout 外部 `dify-plugins` 仓库，提交插件包并创建 PR。

## 错误处理

- tag 与 manifest 版本不一致时立即失败，避免错误版本资产发布。
- 测试失败时不打包、不发 Release。
- Release 已存在时允许覆盖同名 `.difypkg`，便于修复失败重跑。
- 外部 PR 已存在时不让整个发布失败，只输出提示。

## 验证

- 使用 YAML 解析校验 workflow 文件。
- 运行 `uv run --no-sync pytest test/`。
- 运行 `git diff --check`。
