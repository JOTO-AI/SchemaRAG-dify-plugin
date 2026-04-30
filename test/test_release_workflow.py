"""
发布流水线配置测试
"""

from pathlib import Path

import yaml


WORKFLOW_DIR = Path(__file__).resolve().parents[1] / ".github" / "workflows"


def _load_workflow(name: str) -> dict:
    """读取 GitHub Actions workflow，兼容 PyYAML 将 on 解析为布尔值的问题。"""
    workflow = yaml.safe_load((WORKFLOW_DIR / name).read_text())
    if True in workflow and "on" not in workflow:
        workflow["on"] = workflow.pop(True)
    return workflow


def _step_names(workflow: dict) -> list[str]:
    """提取发布 job 的步骤名称。"""
    return [
        step["name"]
        for job in workflow["jobs"].values()
        for step in job["steps"]
        if "name" in step
    ]


def test_plugin_publish_runs_on_every_tag_and_manual_dispatch():
    """发布 workflow 必须由 tag 推送或手动指定 tag 触发"""
    workflow = _load_workflow("plugin-publish.yml")

    assert workflow["on"]["push"]["tags"] == ["*"]
    assert workflow["on"]["workflow_dispatch"]["inputs"]["tag_name"]["required"] is True


def test_plugin_publish_orders_release_before_external_sync():
    """先发布本仓库 Release，再同步外部 dify-plugins PR"""
    workflow = _load_workflow("plugin-publish.yml")
    names = _step_names(workflow)

    assert names.index("Run tests") < names.index("Package plugin")
    assert names.index("Create or update project release") < names.index("Checkout dify-plugins fork")
    assert names.index("Create or update project release") < names.index("Create external dify-plugins PR")


def test_plugin_publish_runs_full_test_suite_before_packaging():
    """发布打包前必须运行完整测试套件"""
    workflow = _load_workflow("plugin-publish.yml")
    test_step = next(
        step
        for step in workflow["jobs"]["publish"]["steps"]
        if step.get("name") == "Run tests"
    )

    assert "uv run --no-sync pytest test/" in test_step["run"]


def test_plugin_publish_uploads_difypkg_with_write_permission():
    """Release 发布需要写权限，并覆盖上传同名 difypkg 方便重跑"""
    workflow = _load_workflow("plugin-publish.yml")
    release_step = next(
        step
        for step in workflow["jobs"]["publish"]["steps"]
        if step.get("name") == "Create or update project release"
    )

    assert workflow["permissions"]["contents"] == "write"
    assert "gh release upload" in release_step["run"]
    assert "--clobber" in release_step["run"]


def test_legacy_publish_no_longer_runs_on_main_push():
    """旧发布入口不能再因 main push 自动执行"""
    workflow = _load_workflow("publish.yml")

    assert workflow["on"] == {"workflow_dispatch": None}


def test_package_check_runs_on_pull_request_and_branch_push():
    """PR 打包验证 workflow 必须在 PR 和普通分支推送时运行"""
    workflow = _load_workflow("package-check.yml")

    assert workflow["on"]["pull_request"]["branches"] == ["main"]
    assert workflow["on"]["push"]["branches"] == ["main", "codex/**", "feature/**", "fix/**"]
    assert "tags" not in workflow["on"]["push"]


def test_package_check_tests_then_packages_plugin():
    """PR 打包验证必须先跑完整测试，再执行 Dify 插件打包"""
    workflow = _load_workflow("package-check.yml")
    names = _step_names(workflow)
    package_step = next(
        step
        for step in workflow["jobs"]["package-check"]["steps"]
        if step.get("name") == "Package plugin"
    )

    assert names.index("Run tests") < names.index("Package plugin")
    assert "uv run --no-sync pytest test/" in next(
        step["run"]
        for step in workflow["jobs"]["package-check"]["steps"]
        if step.get("name") == "Run tests"
    )
    assert "dify-plugin-linux-amd64\" plugin package" in package_step["run"]


def test_package_check_uploads_difypkg_artifact():
    """PR 打包产物应作为 artifact 上传，便于下载检查"""
    workflow = _load_workflow("package-check.yml")
    upload_step = next(
        step
        for step in workflow["jobs"]["package-check"]["steps"]
        if step.get("name") == "Upload package artifact"
    )

    assert upload_step["uses"] == "actions/upload-artifact@v4"
    assert upload_step["with"]["name"] == "dify-plugin-package"
    assert upload_step["with"]["path"] == "*.difypkg"
