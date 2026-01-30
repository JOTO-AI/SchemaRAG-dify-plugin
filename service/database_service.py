import re
from typing import Dict, List, Tuple, Optional
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError, OperationalError, ProgrammingError
from urllib.parse import quote_plus

# 尝试导入达梦数据库驱动和 SQLAlchemy 方言，如果不存在则忽略
try:
    import dmPython
    # 导入 dmSQLAlchemy 以注册 SQLAlchemy 方言
    # dmSQLAlchemy 会自动注册 'dm' 方言到 SQLAlchemy
    import sqlalchemy_dm

    DAMENG_AVAILABLE = True
except ImportError:
    DAMENG_AVAILABLE = False


class DatabaseService:
    """
    数据库服务类，使用 SQLAlchemy 统一管理多种数据库连接和查询执行

    支持的数据库类型：
    - MySQL
    - PostgreSQL
    - SQL Server (MSSQL)
    - Oracle
    - DamengDB (达梦数据库)
    """

    # 数据库驱动映射
    DB_DRIVERS = {
        "mysql": "mysql+pymysql",
        "postgresql": "postgresql+psycopg2",
        "mssql": "mssql+pymssql",
        "oracle": "oracle+oracledb",
        "dameng": "dm+dmPython",  # 达梦数据库
        "doris": "doris+pymysql",  # Apache Doris (使用 MySQL 协议)
    }

    def __init__(self):
        """初始化数据库服务"""
        self._engine_cache: Dict[str, Engine] = {}

    def _build_connection_uri(
        self, db_type: str, host: str, port: int, user: str, password: str, dbname: str
    ) -> str:
        """
        构建 SQLAlchemy 数据库连接 URI

        Args:
            db_type: 数据库类型
            host: 主机地址
            port: 端口号
            user: 用户名
            password: 密码
            dbname: 数据库名

        Returns:
            SQLAlchemy 连接 URI 字符串

        Raises:
            ValueError: 不支持的数据库类型
        """
        if db_type not in self.DB_DRIVERS:
            raise ValueError(f"Unsupported database type: {db_type}")

        # 对密码进行 URL 编码，处理特殊字符
        encoded_password = quote_plus(password)
        encoded_user = quote_plus(user)

        driver = self.DB_DRIVERS[db_type]

        # 针对不同数据库类型构建 URI
        if db_type == "oracle":
            # Oracle 使用 service_name
            return f"{driver}://{encoded_user}:{encoded_password}@{host}:{port}/?service_name={dbname}"
        elif db_type == "dameng":
            # 达梦数据库特殊处理
            if not DAMENG_AVAILABLE:
                raise ValueError(
                    "DamengDB support requires dmPython package to be installed"
                )
            # 达梦使用标准格式
            return (
                f"{driver}://{encoded_user}:{encoded_password}@{host}:{port}/{dbname}"
            )
        else:
            # MySQL, PostgreSQL, MSSQL, Doris 使用标准格式
            return (
                f"{driver}://{encoded_user}:{encoded_password}@{host}:{port}/{dbname}"
            )

    def _get_or_create_engine(
        self, db_type: str, host: str, port: int, user: str, password: str, dbname: str
    ) -> Engine:
        """
        获取或创建 SQLAlchemy 引擎（带缓存）

        Args:
            db_type: 数据库类型
            host: 主机地址
            port: 端口号
            user: 用户名
            password: 密码
            dbname: 数据库名

        Returns:
            SQLAlchemy Engine 实例
        """
        # 创建缓存键（不包含密码以提高安全性）
        cache_key = f"{db_type}://{user}@{host}:{port}/{dbname}"

        if cache_key not in self._engine_cache:
            uri = self._build_connection_uri(
                db_type, host, port, user, password, dbname
            )

            # 创建引擎配置
            engine_args = {
                "pool_pre_ping": True,  # 连接池健康检查
                "pool_recycle": 3600,  # 连接回收时间（秒）
                "echo": False,  # 不输出 SQL 日志
            }

            # 针对特定数据库的额外配置
            if db_type == "mysql" or db_type == "doris":
                # MySQL 和 Doris 使用相同的字符集配置
                engine_args["connect_args"] = {"charset": "utf8mb4"}
            elif db_type == "mssql":
                # SQL Server (pymssql) 配置：charset 使用小写 utf8
                engine_args["connect_args"] = {"charset": "utf8"}
            elif db_type == "oracle":
                # Oracle 使用 thin 模式，需要在 connect_args 中配置
                engine_args["connect_args"] = {"thick_mode": False}
            elif db_type == "dameng":
                # 达梦数据库特殊配置
                engine_args["connect_args"] = {
                    "encoding": "UTF-8",  # 设置字符编码
                }

            self._engine_cache[cache_key] = create_engine(uri, **engine_args)

        return self._engine_cache[cache_key]

    def execute_query(
        self,
        db_type: str,
        host: str,
        port: int,
        user: str,
        password: str,
        dbname: str,
        query: str,
    ) -> Tuple[List[Dict], List[str]]:
        """
        使用 SQLAlchemy 连接数据库并执行查询

        Args:
            db_type: 数据库类型 (mysql, postgresql, mssql, oracle, dameng)
            host: 数据库主机地址
            port: 数据库端口
            user: 数据库用户名
            password: 数据库密码
            dbname: 数据库名称
            query: SQL 查询语句

        Returns:
            Tuple[List[Dict], List[str]]: (查询结果列表, 列名列表)

        Raises:
            ValueError: 参数验证失败或 SQL 语句为空
            SQLAlchemyError: 数据库操作失败
        """
        # 清理 SQL 语句中的 markdown 格式
        match = re.search(r"```(?:sql)?\s*(.*?)\s*```", query, re.DOTALL)
        if match:
            cleaned_sql = match.group(1).strip()
        else:
            cleaned_sql = query.strip()

        if not cleaned_sql:
            raise ValueError("SQL query cannot be empty.")

        try:
            # 获取或创建数据库引擎
            engine = self._get_or_create_engine(
                db_type, host, port, user, password, dbname
            )

            # 使用连接上下文执行查询
            with engine.connect() as connection:
                # 执行 SQL 语句
                result = connection.execute(text(cleaned_sql))

                # 检查是否返回结果集
                if result.returns_rows:
                    # 获取列名
                    columns = list(result.keys())

                    # 获取所有行数据
                    rows = result.fetchall()

                    # 将行数据转换为字典列表
                    results = [dict(zip(columns, row)) for row in rows]

                    return results, columns
                else:
                    # 对于不返回行的查询（INSERT, UPDATE, DELETE 等）
                    return [{"status": "success", "rows_affected": result.rowcount}], [
                        "result"
                    ]

        except (OperationalError, ProgrammingError) as e:
            # 数据库操作错误或 SQL 语法错误
            raise SQLAlchemyError(f"Database operation failed: {str(e)}") from e
        except SQLAlchemyError as e:
            # 其他 SQLAlchemy 错误
            raise SQLAlchemyError(f"SQLAlchemy error: {str(e)}") from e
        except Exception as e:
            # 其他未预期的错误
            raise ValueError(
                f"Unexpected error during query execution: {str(e)}"
            ) from e

    def close_all_connections(self):
        """关闭所有缓存的数据库连接"""
        for engine in self._engine_cache.values():
            engine.dispose()
        self._engine_cache.clear()

    def _format_output(
        self, results: List[Dict], columns: List[str], format_type: str
    ) -> str:
        """
        将查询结果格式化为指定格式

        Args:
            results: 查询结果列表
            columns: 列名列表
            format_type: 输出格式 ('json' 或 'md')

        Returns:
            格式化后的字符串
        """
        if not results:
            return "Query executed successfully, but returned no results."

        df = pd.DataFrame(results, columns=columns)

        if format_type == "json":
            return df.to_json(orient="records", indent=4, force_ascii=False)
        elif format_type == "md":
            return df.to_markdown(index=False)
        else:
            return "Unsupported output format. Please use 'json' or 'md'."

    def __del__(self):
        """析构函数，确保连接被正确关闭"""
        try:
            self.close_all_connections()
        except Exception:
            pass  # 静默处理析构函数中的错误
