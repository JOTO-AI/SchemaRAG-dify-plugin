import os
import logging
from typing import Optional, List
import sys

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)  # 添加上级目录到路径中

from sqlalchemy.engine import Engine
from sqlalchemy import create_engine
from core.m_schema.schema_engine import SchemaEngine

# 尝试导入达梦数据库 SQLAlchemy 方言，如果可用则自动注册
try:
    import dmSQLAlchemy  # noqa: F401
except ImportError:
    pass  # 达梦数据库支持可选
from config import DatabaseConfig, DifyUploadConfig, LoggerConfig
from service.database_connection import (
    DatabaseConnectionError,
    attach_dameng_schema_listener,
    build_connection_uri,
    build_engine_args,
    diagnose_database_exception,
    format_connection_target,
    get_connection_test_sql,
)
from service.dify_service import DifyUploader
from service.network_service import NetworkTester
from utils import (
    Logger,
    normalize_dameng_schema_name,
    normalize_oracle_schema_name,
    read_json,
)


class SchemaRAGBuilder:
    """
    数据字典生成和上传的总控制器。
    支持通过参数传入db_config、logger_config、dify_config等对象进行初始化。
    也可通过from_config_file静态方法从配置文件初始化。
    """

    def __init__(
        self,
        db_config: DatabaseConfig,
        logger_config: LoggerConfig,
        dify_config: Optional[DifyUploadConfig] = None,
        include_tables: Optional[List[str]] = None,
        logger: Optional[logging.Logger] = None,
    ):
        if not isinstance(db_config, DatabaseConfig):
            raise TypeError("db_config必须为DatabaseConfig类型")
        if not isinstance(logger_config, LoggerConfig):
            raise TypeError("logger_config必须为LoggerConfig类型")
        if dify_config is not None and not isinstance(dify_config, DifyUploadConfig):
            raise TypeError("dify_config必须为DifyUploadConfig类型或None")
        self.db_config = db_config
        self.logger_config = logger_config
        self.dify_config = dify_config
        self.include_tables = include_tables
        self.logger_manager = None
        if logger is None:
            self.logger_manager = Logger(self.logger_config)
            self.logger = self.logger_manager.get_logger()
        else:
            self.logger = logger
        self.engine: Optional[Engine] = None
        self.uploader: Optional[DifyUploader] = None
        self.schema_engine: Optional[SchemaEngine] = None
        self._initialize_engine()
        self._initialize_components()

    def _connection_target(self) -> str:
        """生成不含密码的连接目标描述。"""
        return format_connection_target(
            self.db_config.type,
            self.db_config.host,
            self.db_config.port,
            self.db_config.user,
            self.db_config.database,
            schema=self._resolve_schema_name(),
            oracle_connect_type=self.db_config.oracle_connect_type,
        )

    def _raise_diagnostic_error(
        self,
        stage: str,
        error: BaseException,
        *,
        schema: Optional[str] = None,
    ) -> None:
        """记录并抛出带处理建议的数据库诊断错误。"""
        diagnostic = diagnose_database_exception(
            stage,
            self.db_config.type,
            error,
            target=self._connection_target(),
            schema=schema,
            secrets=[self.db_config.password],
        )
        self.logger.error(str(diagnostic))
        raise diagnostic from error

    def _initialize_engine(self) -> None:
        """创建 SQLAlchemy Engine，但不把懒连接误认为连接成功。"""
        target = self._connection_target()
        self.logger.info(f"开始创建数据库引擎: {target}")
        try:
            self.engine = create_engine(
                build_connection_uri(
                    self.db_config.type,
                    self.db_config.host,
                    self.db_config.port,
                    self.db_config.user,
                    self.db_config.password,
                    self.db_config.database,
                    self.db_config.oracle_connect_type,
                ),
                **self._get_engine_args(),
            )
            if self.db_config.type == "dameng":
                attach_dameng_schema_listener(self.engine, self.db_config.database)
            self.logger.info(f"数据库引擎创建完成: {target}")
        except Exception as e:
            self._raise_diagnostic_error("数据库引擎创建", e)

    def _get_engine_args(self) -> dict:
        """
        根据数据库类型获取 SQLAlchemy 引擎参数

        Returns:
            引擎配置参数字典
        """
        return build_engine_args(
            self.db_config.type,
            oracle_thick_mode=self.db_config.oracle_thick_mode,
            oracle_client_lib_dir=self.db_config.oracle_client_lib_dir,
        )

    def _resolve_schema_name(self) -> Optional[str]:
        """根据数据库类型解析用于元数据抽取的 schema/owner。"""
        configured_schema = (self.db_config.schema or "").strip()
        db_type = self.db_config.type

        if configured_schema:
            if db_type == "oracle":
                return normalize_oracle_schema_name(configured_schema)
            if db_type == "dameng":
                return normalize_dameng_schema_name(configured_schema)
            return configured_schema

        if db_type == "oracle":
            return normalize_oracle_schema_name(self.db_config.user)
        if db_type == "dameng":
            return normalize_dameng_schema_name(self.db_config.database)
        if db_type == "postgresql":
            return "public"
        if db_type == "mssql":
            return "dbo"
        if db_type in ["mysql", "doris"]:
            return self.db_config.database

        return None

    @staticmethod
    def from_config_file(
        db_config_path: str,
        logger_config_path: str,
        dify_config_path: Optional[str] = None,
    ) -> "SchemaRAGBuilder":
        """
        可选工厂方法：从配置文件路径初始化SchemaRAGBuilder。
        """
        db_config = read_json(db_config_path)
        logger_config = read_json(logger_config_path)
        dify_config = read_json(dify_config_path) if dify_config_path else None
        # 假设read_json返回dict，需要转为对象
        db_config_obj = DatabaseConfig(**db_config)
        logger_config_obj = LoggerConfig(**logger_config)
        dify_config_obj = DifyUploadConfig(**dify_config) if dify_config else None
        return SchemaRAGBuilder(db_config_obj, logger_config_obj, dify_config_obj)

    def _initialize_components(self):
        """初始化所有服务组件"""
        if not self.engine:
            self.logger.error("数据库引擎未成功创建，无法初始化Schema引擎")
            raise DatabaseConnectionError(
                "数据库引擎创建",
                "SQLAlchemy Engine 未创建",
                "请检查数据库类型、驱动依赖和连接配置。",
            )
        self._check_network_connectivity()
        self._verify_database_connection()

        schema_name = self._resolve_schema_name()
        try:
            self.logger.info(
                f"开始初始化 Schema 引擎: target={self._connection_target()}"
            )
            self.schema_engine = SchemaEngine(
                engine=self.engine,
                schema=schema_name,
                db_name=self.db_config.database,
                include_tables=self.include_tables,
            )
            usable_tables = list(self.schema_engine.get_usable_table_names())
            if not usable_tables:
                raise DatabaseConnectionError(
                    "Schema 反射",
                    f"当前配置下没有可见数据表: {self._connection_target()}",
                    "请确认 Database Schema 是否正确、账号是否有表结构读取权限；如果只配置了 Tables Name，请先清空后重试确认可见表。",
                )
            self.logger.info(
                f"Schema引擎初始化成功，可见表数量: {len(usable_tables)}"
            )
        except DatabaseConnectionError as e:
            self.logger.error(str(e))
            raise
        except Exception as e:
            self._raise_diagnostic_error("Schema 反射", e, schema=schema_name)
        if self.dify_config:
            try:
                self.uploader = DifyUploader(self.dify_config, self.logger)
                self.logger.info("Dify上传器初始化成功")
            except ImportError as e:
                self.logger.error(f"Dify组件初始化失败: {e}")
                self.uploader = None

    def generate_dictionary(self) -> Optional[str]:
        """
        生成数据字典文件。
        :return: 数据字典字符串
        """
        if not self.schema_engine:
            self.logger.error("Schema引擎未初始化，无法生成数据字典")
            raise RuntimeError("Schema引擎未初始化，请检查数据库连接")
        self.logger.info("开始生成数据字典...")
        try:
            mschema = self.schema_engine.mschema
            if not mschema or not mschema.tables:
                self.logger.error("未能获取到可用数据库schema信息")
                raise RuntimeError(
                    "无法获取数据库schema信息：目标 schema 下没有可见表或账号缺少元数据读取权限"
                )
            mschema_str = mschema.to_mschema()
            # if save_path:
            #     if save_path.endswith(".json"):
            #         mschema.save(save_path)
            #     elif save_path.endswith(".txt") or save_path.endswith(".md"):
            #         save_raw_text(save_path, mschema_str)
            #     logging.info(f"数据字典已保存到: {save_path}")
            return mschema_str
        except Exception as e:
            self.logger.error(f"生成数据字典时发生错误: {e}")
            raise

    def upload_file_to_dify(self, file_path: str):
        """
        上传文件到Dify知识库。
        :param file_path: 文件路径
        """
        if not self.uploader:
            self.logger.error("Dify上传功能未启用或初始化失败，无法上传")
            raise RuntimeError("Dify上传功能未启用或初始化失败")
        self.logger.info(f"准备将文件上传到Dify: {file_path}")
        try:
            self.uploader.upload_file(file_path)
        except Exception as e:
            self.logger.error(f"上传文件 {file_path} 到Dify时失败: {e}")
            raise

    def upload_text_to_dify(self, name: str, content: str):
        """
        上传文字到Dify知识库。
        :param name: 文本名称
        :param content: 文本内容
        """
        if not self.uploader:
            self.logger.error("Dify上传功能未启用或初始化失败，无法上传")
            raise RuntimeError("Dify上传功能未启用或初始化失败")
        self.logger.info(f"准备将文字上传到Dify: {name}")
        try:
            self.uploader.upload_text(name=name, content=content)
        except Exception as e:
            self.logger.error(f"上传 {name} 到Dify时失败: {e}")
            raise

    def run_full_process(self):
        """
        执行完整的生成和上传流程。
        """
        try:
            schema_content = self.generate_dictionary()
            name = f"{self.db_config.database}_schema"
            if self.dify_config and schema_content:
                self.upload_text_to_dify(name=name, content=schema_content)
            self.logger.info("所有任务已成功完成！")
        except Exception as e:
            self.logger.error(f"处理流程中发生错误: {e}")
        finally:
            self.close()

    def close(self):
        """关闭数据库连接"""
        if self.engine:
            self.engine.dispose()
            self.logger.info("数据库连接已关闭")

    def _check_network_connectivity(self) -> None:
        """在 DBAPI 登录前先检查插件运行环境到数据库端口的 TCP 连通性。"""
        if self.db_config.type == "sqlite":
            return

        target = self._connection_target()
        self.logger.info(f"开始检查数据库网络连通性: {target}")
        if NetworkTester.test_connectivity(
            self.db_config.host,
            self.db_config.port,
        ):
            self.logger.info(f"数据库网络连通性检查通过: {target}")
            return

        diagnostic = DatabaseConnectionError(
            "网络连通性检查",
            f"插件运行环境无法连接到 {self.db_config.host}:{self.db_config.port}",
            "请确认主机、端口、防火墙、安全组和 Dify plugin_daemon 容器网络；如果数据库在宿主机本机，不要在容器中使用 127.0.0.1。",
        )
        self.logger.error(str(diagnostic))
        raise diagnostic

    def _verify_database_connection(self) -> None:
        """显式打开连接并执行轻量探测 SQL，定位认证与服务名问题。"""
        if not self.engine:
            return

        target = self._connection_target()
        self.logger.info(f"开始验证数据库登录与基础查询: {target}")
        try:
            with self.engine.connect() as connection:
                connection.exec_driver_sql(get_connection_test_sql(self.db_config.type))
            self.logger.info(f"数据库登录与基础查询验证通过: {target}")
        except Exception as e:
            self._raise_diagnostic_error("数据库登录验证", e)
