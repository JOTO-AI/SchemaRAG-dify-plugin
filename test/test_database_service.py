#!/usr/bin/env python3
"""
测试数据库执行服务的 SQL 执行、格式化和 URI 构建行为
"""

import json
from unittest.mock import patch

import pytest

from service.database_service import DatabaseService


class FakeResult:
    """SQLAlchemy Result 测试替身。"""

    def __init__(self, rows=None, columns=None, rowcount=0):
        self._rows = rows or []
        self._columns = columns or []
        self.rowcount = rowcount
        self.returns_rows = columns is not None

    def keys(self):
        return self._columns

    def fetchall(self):
        return self._rows


class FakeConnection:
    """记录 execute 入参的连接替身。"""

    def __init__(self, result):
        self.result = result
        self.executed_sql = None

    def execute(self, statement):
        self.executed_sql = str(statement)
        return self.result


class FakeConnectContext:
    """engine.connect() 返回的上下文管理器替身。"""

    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc, traceback):
        return False


class FakeEngine:
    """仅实现 connect 的 Engine 替身。"""

    def __init__(self, connection):
        self.connection = connection

    def connect(self):
        return FakeConnectContext(self.connection)


def test_execute_query_cleans_markdown_and_returns_rows_as_dicts():
    """execute_query 应清理 markdown SQL，并把行结果转成字典列表。"""
    service = DatabaseService()
    connection = FakeConnection(
        FakeResult(
            rows=[(1, "Alice"), (2, "Bob")],
            columns=["id", "name"],
        )
    )

    with patch.object(service, "_get_or_create_engine", return_value=FakeEngine(connection)):
        rows, columns = service.execute_query(
            "mysql",
            "localhost",
            3306,
            "root",
            "password",
            "app",
            "```sql\nSELECT * FROM users\n```",
        )

    assert connection.executed_sql == "SELECT * FROM users"
    assert columns == ["id", "name"]
    assert rows == [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]


def test_execute_query_returns_rowcount_for_non_select_statements():
    """无返回行的 SQL 应返回统一 success 结构和影响行数。"""
    service = DatabaseService()
    connection = FakeConnection(FakeResult(columns=None, rowcount=3))

    with patch.object(service, "_get_or_create_engine", return_value=FakeEngine(connection)):
        rows, columns = service.execute_query(
            "mysql",
            "localhost",
            3306,
            "root",
            "password",
            "app",
            "UPDATE users SET active = 1",
        )

    assert rows == [{"status": "success", "rows_affected": 3}]
    assert columns == ["result"]


def test_execute_query_rejects_empty_sql_after_cleanup():
    """空 SQL 应在连接数据库前被拒绝。"""
    service = DatabaseService()

    with patch.object(service, "_get_or_create_engine") as get_engine:
        with pytest.raises(ValueError, match="SQL query cannot be empty"):
            service.execute_query(
                "mysql",
                "localhost",
                3306,
                "root",
                "password",
                "app",
                "   ",
            )

    get_engine.assert_not_called()


def test_build_connection_uri_encodes_user_and_password():
    """连接 URI 应 URL 编码用户名和密码中的特殊字符。"""
    service = DatabaseService()

    uri = service._build_connection_uri(
        "postgresql",
        "db.example",
        5432,
        "user@tenant",
        "p@ss#word",
        "app",
    )

    assert uri == (
        "postgresql+psycopg2://user%40tenant:p%40ss%23word@db.example:5432/app"
    )


def test_build_connection_uri_rejects_unsupported_database_type():
    """不支持的数据库类型应抛出明确错误。"""
    with pytest.raises(ValueError, match="Unsupported database type: db2"):
        DatabaseService()._build_connection_uri(
            "db2",
            "localhost",
            50000,
            "user",
            "password",
            "app",
        )


def test_format_output_json_markdown_and_unsupported_format():
    """结果格式化支持 JSON/Markdown，并对未知格式返回提示。"""
    service = DatabaseService()
    rows = [{"id": 1, "name": "张三"}]
    columns = ["id", "name"]

    json_output = service._format_output(rows, columns, "json")
    assert json.loads(json_output) == [{"id": 1, "name": "张三"}]

    md_output = service._format_output(rows, columns, "md")
    assert "张三" in md_output
    assert "id" in md_output

    assert service._format_output(rows, columns, "csv") == (
        "Unsupported output format. Please use 'json' or 'md'."
    )


def test_format_output_handles_empty_results():
    """空结果集应返回明确说明，而不是空字符串。"""
    assert DatabaseService()._format_output([], ["id"], "json") == (
        "Query executed successfully, but returned no results."
    )
