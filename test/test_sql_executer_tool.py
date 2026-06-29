"""
测试 SQL 执行工具的工具层行为。
"""

import json
import sys

for module_name in [
    "dify_plugin",
    "dify_plugin.config",
    "dify_plugin.config.logger_format",
    "dify_plugin.entities",
    "dify_plugin.entities.tool",
    "dify_plugin.errors",
    "dify_plugin.errors.tool",
    "service.plugin_logging",
    "tools.sql_executer",
]:
    sys.modules.pop(module_name, None)

from service.plugin_logging import get_plugin_logger  # noqa: E402
from tools.sql_executer import SQLExecuterTool  # noqa: E402


class FakeDatabaseService:
    """数据库服务替身。"""

    def __init__(self):
        self.calls = []

    def execute_query(self, *args):
        self.calls.append(args)
        return (
            [
                {"id": 1, "amount": 1.0},
                {"id": 2, "amount": 2.5},
                {"id": 3, "amount": 3.25},
            ],
            ["id", "amount"],
        )

    def _format_output(self, results, columns, output_format):
        assert columns == ["id", "amount"]
        assert output_format == "json"
        return json.dumps(results, ensure_ascii=False)


def _create_tool(config_validated: bool = True) -> SQLExecuterTool:
    """创建不依赖 Dify runtime 的工具实例。"""
    tool = object.__new__(SQLExecuterTool)
    tool._db_service = FakeDatabaseService()
    tool._db_config = {
        "db_type": "mysql",
        "db_host": "db.example",
        "db_port": 3306,
        "db_user": "root",
        "db_password": "password",
        "db_name": "app",
        "oracle_connect_type": "service_name",
        "oracle_thick_mode": False,
        "oracle_client_lib_dir": None,
    }
    tool._config_validated = config_validated
    tool.logger = get_plugin_logger("test.sql_executer_tool")
    tool.create_text_message = lambda text=None, **kwargs: text or kwargs.get("text")
    return tool


def test_sql_executer_tool_returns_message_when_provider_config_invalid():
    """Provider 数据库配置无效时工具应直接返回用户可读错误。"""
    tool = _create_tool(config_validated=False)

    outputs = list(tool._invoke({"sql": "SELECT 1"}))

    assert outputs == ["错误: 数据库配置不完整或无效，请检查provider配置"]


def test_sql_executer_tool_executes_cleans_truncates_and_formats_results():
    """工具层应清理 SQL、调用数据库服务、按 max_line 截断并格式化输出。"""
    tool = _create_tool()

    outputs = list(
        tool._invoke(
            {
                "sql": "```sql\nSELECT * FROM orders\n```",
                "output_format": "json",
                "max_line": 2,
            }
        )
    )

    assert len(outputs) == 1
    rows = json.loads(outputs[0])
    assert rows == [
        {"id": "1", "amount": "1"},
        {"id": "2", "amount": "2.5"},
    ]
    call_args = tool._db_service.calls[0]
    assert call_args[:7] == (
        "mysql",
        "db.example",
        3306,
        "root",
        "password",
        "app",
        "SELECT * FROM orders",
    )
