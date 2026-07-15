"""
测试数据库连接 URI、引擎参数和错误诊断。
"""

from sqlalchemy.exc import NoSuchModuleError

from service.database_connection import (
    DatabaseConnectionError,
    build_connection_uri,
    build_engine_args,
    diagnose_database_exception,
    format_connection_target,
    get_connection_test_sql,
    sanitize_error_message,
)


def test_build_connection_uri_encodes_database_name_and_oracle_modes():
    """数据库名、Oracle service_name/SID 应按各驱动格式正确编码。"""
    assert build_connection_uri(
        "mysql",
        "db.example",
        3306,
        "user",
        "p@ss",
        "tenant db",
    ) == "mysql+pymysql://user:p%40ss@db.example:3306/tenant%20db"

    assert build_connection_uri(
        "oracle",
        "oracle.example",
        1521,
        "system",
        "p@ss",
        "ORCLPDB1",
    ) == "oracle+oracledb://system:p%40ss@oracle.example:1521/?service_name=ORCLPDB1"

    assert build_connection_uri(
        "oracle",
        "oracle.example",
        1521,
        "system",
        "p@ss",
        "ORCL",
        "sid",
    ) == "oracle+oracledb://system:p%40ss@oracle.example:1521/ORCL"


def test_build_engine_args_for_major_database_types():
    """各数据库类型应带上对应驱动的超时/字符集参数。"""
    mysql_args = build_engine_args("mysql")
    assert mysql_args["pool_pre_ping"] is True
    assert mysql_args["hide_parameters"] is True
    assert mysql_args["connect_args"]["charset"] == "utf8mb4"
    assert mysql_args["connect_args"]["connect_timeout"] == 10

    pg_args = build_engine_args("postgresql")
    assert pg_args["connect_args"]["connect_timeout"] == 10
    assert pg_args["connect_args"]["application_name"] == "schemarag_dify_plugin"

    mssql_args = build_engine_args("mssql")
    assert mssql_args["connect_args"]["login_timeout"] == 10
    assert mssql_args["connect_args"]["timeout"] == 30

    oracle_args = build_engine_args(
        "oracle",
        oracle_thick_mode=True,
        oracle_client_lib_dir="/opt/oracle/instantclient",
    )
    assert oracle_args["connect_args"]["tcp_connect_timeout"] == 10
    assert oracle_args["connect_args"]["retry_count"] == 1
    assert oracle_args["thick_mode"] == {"lib_dir": "/opt/oracle/instantclient"}


def test_connection_target_and_probe_sql_are_safe_and_dialect_aware():
    """日志目标不能包含密码，探测 SQL 应匹配数据库方言。"""
    target = format_connection_target(
        "oracle",
        "oracle.example",
        1521,
        "system",
        "ORCLPDB1",
        schema="SYSTEM",
        oracle_connect_type="service_name",
    )

    assert target == (
        "oracle://system@oracle.example:1521/ORCLPDB1"
        "?schema=SYSTEM&oracle_connect_type=service_name"
    )
    assert "password" not in target
    assert get_connection_test_sql("oracle") == "SELECT 1 FROM DUAL"
    assert get_connection_test_sql("mysql") == "SELECT 1"


def test_sanitize_error_message_removes_explicit_and_uri_passwords():
    """异常消息中不能泄露明文密码或 URI 密码。"""
    message = sanitize_error_message(
        Exception("connect mysql://root:p@ss@db/app failed with p@ss"),
        secrets=["p@ss"],
    )

    assert "p@ss" not in message
    assert "***" in message


def test_diagnose_database_exception_classifies_common_failures():
    """常见驱动、网络、权限和 schema 错误应转换为可处理诊断。"""
    cases = [
        (
            NoSuchModuleError("sqlalchemy.dialects:doris.pymysql"),
            "无法加载 mysql 方言或驱动",
        ),
        (Exception("connection refused"), "无法建立 TCP/数据库会话"),
        (Exception("Access denied for user root"), "账号认证失败"),
        (Exception("Unknown database app"), "数据库名、服务名或 SID 不匹配"),
        (Exception("permission denied for schema public"), "元数据读取权限不足"),
        (Exception("include_tables {'orders'} not found in database"), "指定表不存在"),
        (Exception("current_schema is invalid"), "schema/owner 配置不可用"),
    ]

    for error, expected in cases:
        diagnostic = diagnose_database_exception(
            "测试阶段",
            "mysql",
            error,
            target="mysql://root@db.example:3306/app",
            schema="public",
            secrets=["secret"],
        )

        assert isinstance(diagnostic, DatabaseConnectionError)
        assert "测试阶段失败" in str(diagnostic)
        assert expected in str(diagnostic)
        assert "处理建议" in str(diagnostic)
