#!/usr/bin/env python3
"""
测试数据库支持配置
"""

import os
import sys
import importlib
from unittest.mock import patch

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DatabaseConfig
from service.database_service import DatabaseService


def _load_schema_builder_class():
    """加载真实 SchemaRAGBuilder，避开其他测试安装的 import stub。"""
    sys.modules.pop("service.schema_builder", None)
    module = importlib.import_module("service.schema_builder")
    return module.SchemaRAGBuilder


def test_database_connections():
    """测试不同数据库类型的连接字符串生成"""

    test_configs = [
        {
            "type": "mysql",
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "password",
            "database": "test_db",
        },
        {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "user": "postgres",
            "password": "password",
            "database": "test_db",
        },
        {
            "type": "mssql",
            "host": "localhost",
            "port": 1433,
            "user": "sa",
            "password": "password",
            "database": "test_db",
        },
        {
            "type": "oracle",
            "host": "localhost",
            "port": 1521,
            "user": "system",
            "password": "password",
            "database": "ORCL",
        },
        {
            "type": "dameng",
            "host": "localhost",
            "port": 5236,
            "user": "SYSDBA",
            "password": "SYSDBA",
            "database": "test_db",
        },
    ]

    print("测试数据库连接字符串生成:")
    print("=" * 60)

    for config in test_configs:
        try:
            db_config = DatabaseConfig(
                type=config["type"],
                host=config["host"],
                port=config["port"],
                user=config["user"],
                password=config["password"],
                database=config["database"],
            )

            connection_string = db_config.get_connection_string()
            print(f"✅ {config['type'].upper():>12}: {connection_string}")

        except Exception as e:
            print(f"❌ {config['type'].upper():>12}: 错误 - {e}")

    print("=" * 60)


def test_oracle_connection_string_uses_service_name_by_default():
    """Oracle 默认使用 service_name 连接格式"""
    db_config = DatabaseConfig(
        type="oracle",
        host="localhost",
        port=1521,
        user="system",
        password="password",
        database="ORCLPDB1",
    )

    assert (
        db_config.get_connection_string()
        == "oracle+oracledb://system:password@localhost:1521/?service_name=ORCLPDB1"
    )


def test_oracle_connection_string_can_use_sid():
    """Oracle 兼容 SID 连接格式"""
    db_config = DatabaseConfig(
        type="oracle",
        host="localhost",
        port=1521,
        user="system",
        password="password",
        database="ORCL",
        oracle_connect_type="sid",
    )

    assert (
        db_config.get_connection_string()
        == "oracle+oracledb://system:password@localhost:1521/ORCL"
    )


def test_schema_builder_oracle_thick_mode_engine_args():
    """Oracle Thick 模式通过 SQLAlchemy thick_mode 参数启用"""
    SchemaRAGBuilder = _load_schema_builder_class()
    builder = object.__new__(SchemaRAGBuilder)
    builder.db_config = DatabaseConfig(
        type="oracle",
        host="localhost",
        port=1521,
        user="u_map",
        password="password",
        database="mgdb",
        oracle_thick_mode=True,
        oracle_client_lib_dir="/opt/oracle/instantclient_19_22",
    )

    engine_args = builder._get_engine_args()

    assert engine_args["connect_args"]["thick_mode_dsn_passthrough"] is False
    assert engine_args["thick_mode"] == {
        "lib_dir": "/opt/oracle/instantclient_19_22"
    }


def test_schema_builder_oracle_defaults_schema_to_login_user():
    """Oracle 未显式配置 schema 时默认使用登录用户名"""
    SchemaRAGBuilder = _load_schema_builder_class()
    builder = object.__new__(SchemaRAGBuilder)
    builder.db_config = DatabaseConfig(
        type="oracle",
        host="localhost",
        port=1521,
        user="u_map",
        password="password",
        database="mgdb",
    )

    assert builder._resolve_schema_name() == "U_MAP"


def test_database_service_oracle_sid_connection_uri():
    """运行时 SQL 执行服务兼容 Oracle SID URI。"""
    service = DatabaseService()

    uri = service._build_connection_uri(
        "oracle",
        "localhost",
        1521,
        "system",
        "password",
        "ORCL",
        "sid",
    )

    assert uri == "oracle+oracledb://system:password@localhost:1521/ORCL"


def test_database_service_oracle_thick_mode_engine_args():
    """运行时 SQL 执行服务透传 Oracle Thick 模式参数。"""
    service = DatabaseService()
    fake_engine = object()

    with patch(
        "service.database_service.create_engine",
        return_value=fake_engine,
    ) as create_engine:
        engine = service._get_or_create_engine(
            "oracle",
            "localhost",
            1521,
            "u_map",
            "password",
            "mgdb",
            oracle_thick_mode=True,
            oracle_client_lib_dir="/opt/oracle/instantclient_19_22",
        )

    assert engine is fake_engine
    engine_args = create_engine.call_args.kwargs
    assert engine_args["connect_args"]["thick_mode_dsn_passthrough"] is False
    assert engine_args["thick_mode"] == {
        "lib_dir": "/opt/oracle/instantclient_19_22"
    }


if __name__ == "__main__":
    test_database_connections()
