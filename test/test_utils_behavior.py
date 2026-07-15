#!/usr/bin/env python3
"""
测试通用工具函数的安全、格式化和缓存行为
"""

import decimal

import pytest

from utils import (
    LRUCache,
    _clean_and_validate_sql,
    create_config_hash,
    examples_to_str,
    format_numeric_values,
    format_single_value,
    normalize_dameng_schema_name,
    normalize_oracle_schema_name,
    safe_port_conversion,
)


def test_clean_and_validate_sql_extracts_markdown_and_normalizes_whitespace():
    """SQL 清洗应提取 markdown 代码块并压缩空白。"""
    sql = """
    ```sql
      SELECT   id,   name
      FROM users
      WHERE status = 'active'
    ```
    """

    cleaned = _clean_and_validate_sql(sql)

    assert cleaned == "SELECT id, name FROM users WHERE status = 'active'"


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE users",
        "select * from users; delete from users",
        "select @@version",
        "select * from information_schema.processlist",
        "select * from users into outfile '/tmp/users.csv'",
    ],
)
def test_clean_and_validate_sql_rejects_dangerous_patterns(sql):
    """SQL 清洗应拒绝危险 DDL/DML、系统变量和敏感系统表访问。"""
    with pytest.raises(ValueError, match="危险的SQL操作"):
        _clean_and_validate_sql(sql)


def test_clean_and_validate_sql_allows_whitelisted_information_schema_views():
    """允许访问被白名单放行的 information_schema 元数据视图。"""
    cleaned = _clean_and_validate_sql(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'users'"
    )

    assert "information_schema.columns" in cleaned


def test_safe_port_conversion_handles_valid_invalid_and_missing_values():
    """端口转换对有效、无效和缺失输入有稳定行为。"""
    assert safe_port_conversion("5432") == 5432
    assert safe_port_conversion(1521) == 1521
    assert safe_port_conversion(None) is None
    assert safe_port_conversion("not-a-port") is None


def test_format_single_value_handles_numeric_edge_cases():
    """数值格式化应避免科学计数法并保留特殊浮点值。"""
    assert format_single_value(10) == "10"
    assert format_single_value(10.0) == "10"
    assert format_single_value(1234.56789) == "1234.56789"
    assert format_single_value(1e-7) == "0.0000001"
    assert format_single_value(1234.567, decimal_places=2) == "1234.57"
    assert format_single_value(float("nan")) is None
    assert format_single_value(float("inf")) == "inf"
    assert format_single_value(True) is True
    assert format_single_value("plain text") == "plain text"


def test_format_numeric_values_formats_each_row_without_mutating_input():
    """批量数值格式化应返回新列表，保留非数值字段。"""
    rows = [{"id": 1, "amount": 12.345, "name": "Alice"}]

    formatted = format_numeric_values(rows)

    assert formatted == [{"id": "1", "amount": "12.345", "name": "Alice"}]
    assert rows == [{"id": 1, "amount": 12.345, "name": "Alice"}]


def test_examples_to_str_filters_private_or_unhelpful_examples():
    """示例值转换应过滤邮箱、链接，并格式化 Decimal。"""
    assert examples_to_str(["a@example.com", "safe"]) == []
    assert examples_to_str(["https://example.com"]) == []
    assert examples_to_str([decimal.Decimal("3.14"), None, "paid"]) == [
        "3.14",
        "paid",
    ]


def test_schema_name_normalization_handles_quoted_and_unquoted_identifiers():
    """达梦和 Oracle 未加引号标识符转大写，加引号时保留大小写。"""
    assert normalize_dameng_schema_name(" app ") == "APP"
    assert normalize_oracle_schema_name(" u_map ") == "U_MAP"
    assert normalize_oracle_schema_name('"MixedCase"') == "MixedCase"
    assert normalize_dameng_schema_name('"A""B"') == 'A"B'
    assert normalize_oracle_schema_name(None) is None


def test_create_config_hash_excludes_password_from_cache_key():
    """数据库配置缓存键不应因为密码变化而改变。"""
    base_config = {
        "db_type": "mysql",
        "db_host": "localhost",
        "db_port": 3306,
        "db_name": "sales",
        "db_user": "root",
        "db_password": "old-secret",
    }
    changed_password = base_config | {"db_password": "new-secret"}

    assert create_config_hash(base_config) == create_config_hash(changed_password)


def test_lru_cache_eviction_and_recency_update():
    """LRU 缓存应淘汰最久未使用项，并在 get 后更新使用顺序。"""
    cache = LRUCache(max_size=2)
    cache.put("a", 1)
    cache.put("b", 2)

    assert cache.get("a") == 1
    cache.put("c", 3)

    assert cache.contains("a")
    assert not cache.contains("b")
    assert cache.get("c") == 3
    assert cache.size() == 2
