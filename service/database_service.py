import os
import re
from typing import Dict, List, Tuple, Optional
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError, OperationalError, ProgrammingError
from service.database_connection import (
    DB_DRIVERS as DATABASE_DRIVERS,
    DatabaseConnectionError,
    attach_dameng_schema_listener,
    build_connection_uri,
    build_engine_args,
    diagnose_database_exception,
    format_connection_target,
)


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
    DB_DRIVERS = DATABASE_DRIVERS

    def __init__(self):
        """初始化数据库服务"""
        self._engine_cache: Dict[str, Engine] = {}

    def _is_oracle_thick_mode_enabled(
        self, oracle_thick_mode: Optional[bool] = None
    ) -> bool:
        """判断是否启用 Oracle Thick 模式。"""
        if oracle_thick_mode is not None:
            return oracle_thick_mode
        return os.environ.get("ORACLE_THICK_MODE", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "y",
            "on",
        }

    def _get_oracle_client_lib_dir(
        self, oracle_client_lib_dir: Optional[str] = None
    ) -> Optional[str]:
        """获取 Oracle Client 库路径。"""
        value = oracle_client_lib_dir or os.environ.get("ORACLE_CLIENT_LIB_DIR")
        if value is None:
            return None
        value = value.strip()
        return value or None

    def _build_connection_uri(
        self,
        db_type: str,
        host: str,
        port: int,
        user: str,
        password: str,
        dbname: str,
        oracle_connect_type: str = "service_name",
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
        return build_connection_uri(
            db_type,
            host,
            port,
            user,
            password,
            dbname,
            oracle_connect_type,
        )

    def _get_or_create_engine(
        self,
        db_type: str,
        host: str,
        port: int,
        user: str,
        password: str,
        dbname: str,
        oracle_connect_type: str = "service_name",
        oracle_thick_mode: Optional[bool] = None,
        oracle_client_lib_dir: Optional[str] = None,
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
        thick_enabled = self._is_oracle_thick_mode_enabled(oracle_thick_mode)
        client_lib_dir = self._get_oracle_client_lib_dir(oracle_client_lib_dir) or ""
        cache_key = (
            f"{db_type}://{user}@{host}:{port}/{dbname}"
            f"?oracle_connect_type={oracle_connect_type}"
            f"&oracle_thick_mode={thick_enabled}"
            f"&oracle_client_lib_dir={client_lib_dir}"
        )

        if cache_key not in self._engine_cache:
            uri = self._build_connection_uri(
                db_type, host, port, user, password, dbname, oracle_connect_type
            )

            engine_args = build_engine_args(
                db_type,
                oracle_thick_mode=thick_enabled,
                oracle_client_lib_dir=client_lib_dir,
            )

            engine = create_engine(uri, **engine_args)

            if db_type == "dameng":
                attach_dameng_schema_listener(engine, dbname)

            self._engine_cache[cache_key] = engine

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
        oracle_connect_type: str = "service_name",
        oracle_thick_mode: Optional[bool] = None,
        oracle_client_lib_dir: Optional[str] = None,
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

        target = format_connection_target(
            db_type,
            host,
            port,
            user,
            dbname,
            oracle_connect_type=oracle_connect_type,
        )

        try:
            # 获取或创建数据库引擎
            engine = self._get_or_create_engine(
                db_type,
                host,
                port,
                user,
                password,
                dbname,
                oracle_connect_type,
                oracle_thick_mode,
                oracle_client_lib_dir,
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

        except OperationalError as e:
            # 连接、认证、库名等运行时配置问题需要保留诊断阶段
            raise diagnose_database_exception(
                "SQL 执行连接",
                db_type,
                e,
                target=target,
                secrets=[password],
            ) from e
        except ProgrammingError as e:
            # SQL 语法/对象错误保留为数据库操作错误，便于 SQL Refiner 使用
            raise SQLAlchemyError(f"Database operation failed: {str(e)}") from e
        except DatabaseConnectionError:
            raise
        except ValueError as e:
            raise diagnose_database_exception(
                "SQL 执行连接初始化",
                db_type,
                e,
                target=target,
                secrets=[password],
            ) from e
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
