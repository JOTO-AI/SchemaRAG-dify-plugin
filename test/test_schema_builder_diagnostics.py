"""
测试 Schema 构建阶段的数据库连接诊断。
"""

import importlib
import logging
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from config import DatabaseConfig, LoggerConfig
from service.database_connection import DatabaseConnectionError


def _load_schema_builder_class():
    """加载真实 SchemaRAGBuilder，避开 Provider 测试安装的 import stub。"""
    sys.modules.pop("service.schema_builder", None)
    module = importlib.import_module("service.schema_builder")
    return module.SchemaRAGBuilder


class FakeConnection:
    """最小连接替身，用于验证连接探测 SQL。"""

    def __init__(self):
        self.executed_sql = None

    def exec_driver_sql(self, sql):
        self.executed_sql = sql

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


class FakeEngine:
    """最小 Engine 替身。"""

    def __init__(self):
        self.connection = FakeConnection()
        self.dialect = SimpleNamespace(name="mysql")
        self.url = SimpleNamespace(username="root")
        self.disposed = False

    def connect(self):
        return self.connection

    def dispose(self):
        self.disposed = True


def _db_config() -> DatabaseConfig:
    return DatabaseConfig(
        type="mysql",
        host="db.example",
        port=3306,
        user="root",
        password="password",
        database="app",
    )


def test_schema_builder_reports_network_connectivity_stage():
    """网络不可达时应明确停在网络连通性检查阶段。"""
    SchemaRAGBuilder = _load_schema_builder_class()

    with patch("service.schema_builder.create_engine", return_value=FakeEngine()):
        with patch(
            "service.schema_builder.NetworkTester.test_connectivity",
            return_value=False,
        ):
            with pytest.raises(DatabaseConnectionError) as context:
                SchemaRAGBuilder(
                    _db_config(),
                    LoggerConfig(log_level="INFO"),
                    logger=logging.getLogger("test.schema_builder.network"),
                )

    message = str(context.value)
    assert "网络连通性检查失败" in message
    assert "db.example:3306" in message
    assert "plugin_daemon" in message


def test_schema_builder_reports_schema_reflection_stage_for_missing_tables():
    """表名不可见时应明确停在 Schema 反射阶段并给出处理建议。"""
    SchemaRAGBuilder = _load_schema_builder_class()

    with patch("service.schema_builder.create_engine", return_value=FakeEngine()):
        with patch(
            "service.schema_builder.NetworkTester.test_connectivity",
            return_value=True,
        ):
            with patch(
                "service.schema_builder.SchemaEngine",
                side_effect=ValueError("include_tables {'orders'} not found in database"),
            ):
                with pytest.raises(DatabaseConnectionError) as context:
                    SchemaRAGBuilder(
                        _db_config(),
                        LoggerConfig(log_level="INFO"),
                        include_tables=["orders"],
                        logger=logging.getLogger("test.schema_builder.schema"),
                    )

    message = str(context.value)
    assert "Schema 反射失败" in message
    assert "指定表不存在或当前账号不可见" in message
    assert "Tables Name" in message


def test_schema_builder_rejects_empty_visible_tables():
    """目标 schema 没有可见表时不应生成空数据字典。"""
    SchemaRAGBuilder = _load_schema_builder_class()
    fake_schema_engine = SimpleNamespace(get_usable_table_names=lambda: [])

    with patch("service.schema_builder.create_engine", return_value=FakeEngine()):
        with patch(
            "service.schema_builder.NetworkTester.test_connectivity",
            return_value=True,
        ):
            with patch(
                "service.schema_builder.SchemaEngine",
                return_value=fake_schema_engine,
            ):
                with pytest.raises(DatabaseConnectionError) as context:
                    SchemaRAGBuilder(
                        _db_config(),
                        LoggerConfig(log_level="INFO"),
                        logger=logging.getLogger("test.schema_builder.empty"),
                    )

    assert "Schema 反射失败" in str(context.value)
    assert "没有可见数据表" in str(context.value)


def test_schema_builder_success_path_verifies_connection_and_generates_dictionary():
    """正常路径应先执行连接探测，再初始化 SchemaEngine 并生成数据字典。"""
    SchemaRAGBuilder = _load_schema_builder_class()
    fake_engine = FakeEngine()
    fake_mschema = SimpleNamespace(
        tables={"users": {}},
        to_mschema=lambda: "【DB_ID】 app\n# Table: users",
    )
    fake_schema_engine = SimpleNamespace(
        get_usable_table_names=lambda: ["users"],
        mschema=fake_mschema,
    )

    with patch("service.schema_builder.create_engine", return_value=fake_engine):
        with patch(
            "service.schema_builder.NetworkTester.test_connectivity",
            return_value=True,
        ) as connectivity:
            with patch(
                "service.schema_builder.SchemaEngine",
                return_value=fake_schema_engine,
            ) as schema_engine_class:
                builder = SchemaRAGBuilder(
                    _db_config(),
                    LoggerConfig(log_level="INFO"),
                    logger=logging.getLogger("test.schema_builder.success"),
                )

    assert fake_engine.connection.executed_sql == "SELECT 1"
    connectivity.assert_called_once_with("db.example", 3306)
    schema_engine_class.assert_called_once()
    assert builder.generate_dictionary() == "【DB_ID】 app\n# Table: users"
