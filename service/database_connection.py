"""
数据库连接配置与诊断工具。
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Optional
from urllib.parse import quote, quote_plus

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import NoSuchModuleError

from utils import normalize_dameng_schema_name, quote_dameng_identifier


try:
    import dmPython  # noqa: F401
    import dmSQLAlchemy  # noqa: F401

    DAMENG_AVAILABLE = True
except ImportError:
    DAMENG_AVAILABLE = False


DEFAULT_CONNECT_TIMEOUT = 10
DEFAULT_QUERY_TIMEOUT = 30
DEFAULT_POOL_RECYCLE = 3600
DEFAULT_POOL_TIMEOUT = 30


DB_DRIVERS = {
    "mysql": "mysql+pymysql",
    "postgresql": "postgresql+psycopg2",
    "mssql": "mssql+pymssql",
    "oracle": "oracle+oracledb",
    "dameng": "dm+dmPython",
    # Apache Doris 兼容 MySQL 协议，使用内置 MySQL 方言避免缺少 doris 方言插件。
    "doris": "mysql+pymysql",
}


class DatabaseConnectionError(RuntimeError):
    """带阶段与处理建议的数据库连接诊断错误。"""

    def __init__(
        self,
        stage: str,
        message: str,
        suggestion: str,
        *,
        original: Optional[BaseException] = None,
    ):
        self.stage = stage
        self.message = message
        self.suggestion = suggestion
        self.original = original
        super().__init__(self.__str__())

    def __str__(self) -> str:
        return (
            f"{self.stage}失败：{self.message}\n"
            f"处理建议：{self.suggestion}"
        )


def build_connection_uri(
    db_type: str,
    host: str,
    port: int,
    user: str,
    password: str,
    dbname: str,
    oracle_connect_type: str = "service_name",
) -> str:
    """构建 SQLAlchemy 数据库连接 URI。"""
    if db_type not in DB_DRIVERS:
        raise ValueError(f"Unsupported database type: {db_type}")

    encoded_user = quote_plus(user)
    encoded_password = quote_plus(password)
    encoded_dbname = quote(str(dbname or ""), safe="")
    driver = DB_DRIVERS[db_type]

    if db_type == "oracle":
        connect_type = (oracle_connect_type or "service_name").strip().lower()
        if connect_type == "sid":
            sid = quote(str(dbname or ""), safe="")
            return f"{driver}://{encoded_user}:{encoded_password}@{host}:{port}/{sid}"

        service_name = quote_plus(str(dbname or ""))
        return (
            f"{driver}://{encoded_user}:{encoded_password}@{host}:{port}/"
            f"?service_name={service_name}"
        )

    if db_type == "dameng":
        if not DAMENG_AVAILABLE:
            raise ValueError(
                "DamengDB support requires dmPython package to be installed"
            )
        # dmPython.connect() 不接受 database 参数，schema 通过会话事件切换。
        return f"{driver}://{encoded_user}:{encoded_password}@{host}:{port}"

    return f"{driver}://{encoded_user}:{encoded_password}@{host}:{port}/{encoded_dbname}"


def build_engine_args(
    db_type: str,
    oracle_thick_mode: bool = False,
    oracle_client_lib_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """根据数据库类型生成 SQLAlchemy Engine 参数。"""
    engine_args: Dict[str, Any] = {
        "pool_pre_ping": True,
        "pool_recycle": DEFAULT_POOL_RECYCLE,
        "pool_timeout": DEFAULT_POOL_TIMEOUT,
        "hide_parameters": True,
        "echo": False,
    }

    connect_args: Dict[str, Any] = {}

    if db_type in ["mysql", "doris"]:
        connect_args.update(
            {
                "charset": "utf8mb4",
                "connect_timeout": DEFAULT_CONNECT_TIMEOUT,
                "read_timeout": DEFAULT_QUERY_TIMEOUT,
                "write_timeout": DEFAULT_QUERY_TIMEOUT,
            }
        )
    elif db_type == "postgresql":
        connect_args.update(
            {
                "connect_timeout": DEFAULT_CONNECT_TIMEOUT,
                "application_name": "schemarag_dify_plugin",
            }
        )
    elif db_type == "mssql":
        connect_args.update(
            {
                "charset": "utf8",
                "login_timeout": DEFAULT_CONNECT_TIMEOUT,
                "timeout": DEFAULT_QUERY_TIMEOUT,
            }
        )
    elif db_type == "oracle":
        connect_args.update(
            {
                "thick_mode_dsn_passthrough": False,
                "tcp_connect_timeout": DEFAULT_CONNECT_TIMEOUT,
                "retry_count": 1,
                "retry_delay": 1,
            }
        )
        if oracle_thick_mode:
            client_lib_dir = (oracle_client_lib_dir or "").strip()
            engine_args["thick_mode"] = (
                {"lib_dir": client_lib_dir} if client_lib_dir else True
            )

    if connect_args:
        engine_args["connect_args"] = connect_args

    return engine_args


def attach_dameng_schema_listener(engine: Engine, dbname: Optional[str]) -> None:
    """达梦连接建立后切换 CURRENT_SCHEMA。"""
    normalized_dbname = normalize_dameng_schema_name(dbname)
    if not normalized_dbname:
        return

    quoted_dbname = quote_dameng_identifier(normalized_dbname)

    @event.listens_for(engine, "connect")
    def set_schema(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute(f"ALTER SESSION SET CURRENT_SCHEMA = {quoted_dbname}")
        cursor.close()


def get_connection_test_sql(db_type: str) -> str:
    """返回连接探测 SQL。"""
    if db_type == "oracle":
        return "SELECT 1 FROM DUAL"
    return "SELECT 1"


def format_connection_target(
    db_type: str,
    host: Optional[str],
    port: Optional[int],
    user: Optional[str],
    dbname: Optional[str],
    schema: Optional[str] = None,
    oracle_connect_type: Optional[str] = None,
) -> str:
    """生成不含密码的连接目标描述，便于日志排障。"""
    target = (
        f"{db_type}://{user or '<empty>'}@"
        f"{host or '<empty>'}:{port or '<empty>'}/{dbname or '<empty>'}"
    )
    extras = []
    if schema:
        extras.append(f"schema={schema}")
    if db_type == "oracle":
        extras.append(f"oracle_connect_type={oracle_connect_type or 'service_name'}")
    if extras:
        target = f"{target}?{'&'.join(extras)}"
    return target


def sanitize_error_message(
    error: BaseException,
    secrets: Optional[Iterable[Optional[str]]] = None,
) -> str:
    """清理异常消息中的敏感信息。"""
    message = str(error)
    for secret in secrets or []:
        if secret:
            message = message.replace(str(secret), "***")
    message = re.sub(r"://([^:/@\s]+):([^@/\s]+)@", r"://\1:***@", message)
    return message


def diagnose_database_exception(
    stage: str,
    db_type: str,
    error: BaseException,
    *,
    target: Optional[str] = None,
    schema: Optional[str] = None,
    secrets: Optional[Iterable[Optional[str]]] = None,
) -> DatabaseConnectionError:
    """将底层连接/反射异常转换为用户可处理的诊断信息。"""
    raw_message = sanitize_error_message(error, secrets)
    message_lower = raw_message.lower()
    target_text = f"目标 {target}，" if target else ""
    schema_text = f"schema/owner={schema}，" if schema else ""

    if isinstance(error, NoSuchModuleError) or "can't load plugin" in message_lower:
        return DatabaseConnectionError(
            stage,
            f"{target_text}SQLAlchemy 无法加载 {db_type} 方言或驱动：{raw_message}",
            "请确认插件运行环境已安装对应驱动；Doris 使用 MySQL 协议时应走 mysql+pymysql，达梦需在 Linux/Windows 环境安装 dmPython 与 dmSQLAlchemy。",
            original=error,
        )

    if "dmpython" in message_lower and "requires" in message_lower:
        return DatabaseConnectionError(
            stage,
            f"{target_text}达梦驱动不可用：{raw_message}",
            "请在 Dify plugin_daemon 对应运行环境安装 dmPython 与 dmSQLAlchemy；macOS 本地调试可跳过达梦依赖或使用 Linux 容器。",
            original=error,
        )

    if any(
        marker in message_lower
        for marker in [
            "timed out",
            "timeout",
            "connection refused",
            "could not connect",
            "can't connect",
            "no route to host",
            "name or service not known",
            "temporary failure in name resolution",
            "unknown host",
            "adaptive server is unavailable",
            "ora-12541",
            "ora-12545",
        ]
    ):
        return DatabaseConnectionError(
            stage,
            f"{target_text}无法建立 TCP/数据库会话：{raw_message}",
            "请确认主机、端口、防火墙和 Dify plugin_daemon 容器网络可达；本机数据库在 Docker 中通常不能填 127.0.0.1，需要使用可从容器访问的地址。",
            original=error,
        )

    if any(
        marker in message_lower
        for marker in [
            "access denied",
            "password authentication failed",
            "login failed",
            "authentication failed",
            "ora-01017",
            "用户名",
            "口令",
        ]
    ):
        return DatabaseConnectionError(
            stage,
            f"{target_text}账号认证失败：{raw_message}",
            "请确认用户名、密码、认证方式和来源 IP 白名单；密码中的 @、#、/、空格等特殊字符需要按表单原文填写，插件会自动 URL 编码。",
            original=error,
        )

    if any(
        marker in message_lower
        for marker in [
            "unknown database",
            "database does not exist",
            "does not exist",
            "cannot open database",
            "ora-12514",
            "ora-12505",
            "ora-12154",
        ]
    ):
        return DatabaseConnectionError(
            stage,
            f"{target_text}数据库名、服务名或 SID 不匹配：{raw_message}",
            "请确认 Database Name 的含义：MySQL/PostgreSQL/Doris 为数据库名，Oracle 默认为 service_name，可切换 SID；SQL Server 需确认登录账号有权打开该数据库。",
            original=error,
        )

    if any(
        marker in message_lower
        for marker in [
            "permission denied",
            "insufficient privileges",
            "not authorized",
            "select command denied",
            "ora-01031",
        ]
    ):
        return DatabaseConnectionError(
            stage,
            f"{target_text}{schema_text}元数据读取权限不足：{raw_message}",
            "请给账号授予读取表、列、注释、外键等元数据的权限，至少需要能查看目标 schema 下的表结构并执行轻量只读探测查询。",
            original=error,
        )

    if "include_tables" in message_lower or "not found in database" in message_lower:
        return DatabaseConnectionError(
            stage,
            f"{target_text}{schema_text}指定表不存在或当前账号不可见：{raw_message}",
            "请检查 Tables Name 是否拼写正确、是否需要带大小写引号，或先清空该配置让插件扫描当前 schema 下的可见表。",
            original=error,
        )

    if "schema" in message_lower or "current_schema" in message_lower:
        return DatabaseConnectionError(
            stage,
            f"{target_text}{schema_text}schema/owner 配置不可用：{raw_message}",
            "请确认 Database Schema 是否存在且当前账号有权限；Oracle/达梦未加引号的 schema 会按数据库规则转为大写。",
            original=error,
        )

    return DatabaseConnectionError(
        stage,
        f"{target_text}{schema_text}{raw_message}",
        "请根据上面的原始错误检查驱动、网络、账号、数据库名、schema 与表权限；若仍无法定位，请把该阶段日志提供给管理员排查。",
        original=error,
    )
