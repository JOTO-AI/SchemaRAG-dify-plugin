#!/usr/bin/env python3
"""
测试 Provider 凭据校验异常类型
"""

import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class ToolProviderCredentialValidationError(Exception):
    """测试用 Dify 凭据校验异常"""


def _install_provider_import_stubs():
    """安装 Provider 单元测试所需的最小依赖桩。"""
    dify_plugin = types.ModuleType("dify_plugin")
    errors = types.ModuleType("dify_plugin.errors")
    tool_errors = types.ModuleType("dify_plugin.errors.tool")
    tools_text2sql = types.ModuleType("tools.text2sql")
    tools_sql_executer = types.ModuleType("tools.sql_executer")
    schema_builder = types.ModuleType("service.schema_builder")
    logger_format = types.ModuleType("dify_plugin.config.logger_format")
    config_module = types.ModuleType("dify_plugin.config")

    class ToolProvider:
        pass

    class Text2SQLTool:
        pass

    class SQLExecuterTool:
        pass

    class SchemaRAGBuilder:
        pass

    dify_plugin.ToolProvider = ToolProvider
    tool_errors.ToolProviderCredentialValidationError = (
        ToolProviderCredentialValidationError
    )
    tools_text2sql.Text2SQLTool = Text2SQLTool
    tools_sql_executer.SQLExecuterTool = SQLExecuterTool
    schema_builder.SchemaRAGBuilder = SchemaRAGBuilder
    logger_format.plugin_logger_handler = None

    sys.modules["dify_plugin"] = dify_plugin
    sys.modules["dify_plugin.errors"] = errors
    sys.modules["dify_plugin.errors.tool"] = tool_errors
    sys.modules["dify_plugin.config"] = config_module
    sys.modules["dify_plugin.config.logger_format"] = logger_format
    sys.modules["tools.text2sql"] = tools_text2sql
    sys.modules["tools.sql_executer"] = tools_sql_executer
    sys.modules["service.schema_builder"] = schema_builder


_install_provider_import_stubs()

from provider.build_schema_rag import SchemaRAGBuilderProvider  # noqa: E402


VALID_CREDENTIALS = {
    "api_uri": "http://localhost/v1",
    "dataset_api_key": "dataset-test",
    "db_type": "mysql",
    "db_host": "localhost",
    "db_port": "3306",
    "db_user": "root",
    "db_password": "password",
    "db_name": "test_db",
}


class TestProviderCredentials(unittest.TestCase):
    """Provider 凭据校验测试"""

    def setUp(self):
        """测试前准备"""
        self.provider = SchemaRAGBuilderProvider()

    def test_missing_required_credential_raises_dify_validation_error(self):
        """缺少必要凭据时抛出 Dify 官方凭据校验异常"""
        credentials = VALID_CREDENTIALS | {"api_uri": ""}

        with self.assertRaises(ToolProviderCredentialValidationError):
            self.provider._validate_credentials(credentials)

    def test_build_failure_is_wrapped_as_dify_validation_error(self):
        """Schema RAG 构建失败时包装为 Dify 官方凭据校验异常"""
        with patch.object(
            self.provider,
            "_build_schema_rag",
            side_effect=RuntimeError("数据库连接失败"),
        ):
            with self.assertRaises(ToolProviderCredentialValidationError) as context:
                self.provider._validate_credentials(VALID_CREDENTIALS)

        self.assertIn("数据库连接失败", str(context.exception))

    def test_valid_credentials_trigger_schema_build(self):
        """凭据完整时继续触发现有 Schema RAG 构建流程"""
        with patch.object(self.provider, "_build_schema_rag") as build_schema:
            self.provider._validate_credentials(VALID_CREDENTIALS)

        build_schema.assert_called_once_with(VALID_CREDENTIALS)


if __name__ == "__main__":
    unittest.main()
