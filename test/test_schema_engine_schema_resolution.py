#!/usr/bin/env python3
"""
测试 SchemaEngine 初始化时的 schema/owner 选择逻辑
"""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from core.m_schema.m_schema import MSchema
from core.m_schema.schema_engine import SchemaEngine


class FakeEngine:
    """SchemaEngine 测试用最小 Engine。"""

    def __init__(self, dialect_name: str, username: str = "app_user"):
        self.dialect = SimpleNamespace(name=dialect_name)
        self.url = SimpleNamespace(username=username)


class FakeMetadata:
    """记录 reflect 入参，避免访问真实数据库。"""

    def __init__(self):
        self.tables = {}
        self.reflect_calls = []

    def reflect(self, **kwargs):
        self.reflect_calls.append(kwargs)


class FakeInspector:
    """记录 Inspector schema 入参。"""

    def __init__(self, expected_schema: str):
        self.expected_schema = expected_schema
        self.table_name_schema_calls = []
        self.has_table_calls = []
        self.default_schema_name = expected_schema

    def get_table_names(self, schema=None):
        self.table_name_schema_calls.append(schema)
        if schema != self.expected_schema:
            raise AssertionError(
                f"expected schema {self.expected_schema!r}, got {schema!r}"
            )
        return ["T_USER"]

    def get_view_names(self, schema=None):
        return []

    def has_table(self, table_name, schema=None):
        self.has_table_calls.append((table_name, schema))
        return schema == self.expected_schema

    def get_schema_names(self):
        raise AssertionError("不应在已知 schema 时扫描所有 schema")


class TestSchemaEngineSchemaResolution(unittest.TestCase):
    """SchemaEngine schema/owner 推导测试。"""

    def _build_schema_engine(
        self,
        dialect_name: str,
        expected_schema: str,
        db_name: str = "test_db",
        username: str = "app_user",
        schema=None,
    ):
        inspector = FakeInspector(expected_schema)
        metadata = FakeMetadata()
        engine = FakeEngine(dialect_name=dialect_name, username=username)

        with patch("core.m_schema.sql_database.inspect", return_value=inspector):
            schema_engine = SchemaEngine(
                engine=engine,
                schema=schema,
                metadata=metadata,
                db_name=db_name,
                mschema=MSchema(db_id=db_name, schema=expected_schema),
            )

        return schema_engine, inspector, metadata

    def test_oracle_defaults_to_login_user_schema_before_reflection(self):
        """Oracle 默认使用登录用户作为 schema，避免扫描系统 schema。"""
        schema_engine, inspector, metadata = self._build_schema_engine(
            dialect_name="oracle",
            expected_schema="U_MAP",
            username="u_map",
            db_name="mgdb",
        )

        self.assertEqual(["U_MAP"], inspector.table_name_schema_calls)
        self.assertEqual("U_MAP", metadata.reflect_calls[0]["schema"])
        self.assertEqual({"T_USER": "U_MAP"}, schema_engine._tables_schemas)

    def test_postgresql_defaults_to_public_before_reflection(self):
        """PostgreSQL 默认使用 public schema。"""
        schema_engine, inspector, metadata = self._build_schema_engine(
            dialect_name="postgresql",
            expected_schema="public",
            db_name="business_db",
        )

        self.assertEqual(["public"], inspector.table_name_schema_calls)
        self.assertEqual("public", metadata.reflect_calls[0]["schema"])
        self.assertEqual({"T_USER": "public"}, schema_engine._tables_schemas)

    def test_dameng_defaults_to_normalized_database_owner_before_reflection(self):
        """达梦默认将数据库名规范化为 owner/schema。"""
        schema_engine, inspector, metadata = self._build_schema_engine(
            dialect_name="dm",
            expected_schema="DM_APP",
            db_name="dm_app",
        )

        self.assertEqual(["DM_APP"], inspector.table_name_schema_calls)
        self.assertEqual("DM_APP", metadata.reflect_calls[0]["schema"])
        self.assertEqual({"T_USER": "DM_APP"}, schema_engine._tables_schemas)

    def test_configured_oracle_schema_is_respected(self):
        """显式配置 Oracle schema 时优先生效。"""
        schema_engine, inspector, metadata = self._build_schema_engine(
            dialect_name="oracle",
            expected_schema="REPORTING",
            username="u_map",
            db_name="mgdb",
            schema="REPORTING",
        )

        self.assertEqual(["REPORTING"], inspector.table_name_schema_calls)
        self.assertEqual("REPORTING", metadata.reflect_calls[0]["schema"])
        self.assertEqual({"T_USER": "REPORTING"}, schema_engine._tables_schemas)


if __name__ == "__main__":
    unittest.main()
