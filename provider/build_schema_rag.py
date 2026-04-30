import os
from typing import Any
import sys
import logging
from venv import logger


sys.path.append(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)  # 添加上级目录到路径中

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError
from tools.text2sql import Text2SQLTool
from tools.sql_executer import SQLExecuterTool
from config import DatabaseConfig, LoggerConfig, DifyUploadConfig
from service.schema_builder import SchemaRAGBuilder
from dify_plugin.config.logger_format import plugin_logger_handler


class SchemaRAGBuilderProvider(ToolProvider):
    """
    Schema RAG Builder Provider
    """

    def _get_default_port(self, db_type: str) -> int:
        """
        根据数据库类型获取默认端口
        """
        port_mapping = {
            "mysql": 3306,
            "postgresql": 5432,
            "mssql": 1433,
            "oracle": 1521,
            "dameng": 5236,
            "doris": 9030,
        }
        return port_mapping.get(db_type, 3306)

    def _parse_db_port(self, credentials: dict[str, Any]) -> int:
        """
        解析 Dify 文本输入中的数据库端口
        """
        db_type = credentials.get("db_type")
        db_port = credentials.get("db_port")
        if db_port in (None, ""):
            return self._get_default_port(db_type)
        try:
            return int(db_port)
        except (TypeError, ValueError) as exc:
            raise ValueError("Database port must be a valid integer") from exc

    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        """
        Validate the credentials and build schema RAG
        """
        try:
            # 验证必要的凭据
            api_uri = credentials.get("api_uri")
            dataset_api_key = credentials.get("dataset_api_key")
            db_type = credentials.get("db_type")
            db_host = credentials.get("db_host")
            db_user = credentials.get("db_user")
            db_password = credentials.get("db_password")
            db_name = credentials.get("db_name")
            # build_rag = credentials.get("build_rag", True)

            # 验证API相关参数
            if not api_uri:
                raise ToolProviderCredentialValidationError("API URI is required")

            if not dataset_api_key:
                raise ToolProviderCredentialValidationError(
                    "Dataset API key is required"
                )

            # 验证数据库相关参数
            if not db_type:
                raise ToolProviderCredentialValidationError(
                    "Database type is required"
                )

            # SQLite 只需要数据库名称（文件路径）
            if db_type == "sqlite":
                if not db_name:
                    raise ToolProviderCredentialValidationError(
                        "Database name (file path) is required for SQLite"
                    )
            elif db_type == "doris":
                # Doris需要host, port, user, password, database
                if not db_host:
                    raise ToolProviderCredentialValidationError(
                        "Doris database host is required"
                    )
                if not db_user:
                    raise ToolProviderCredentialValidationError(
                        "Doris database user is required"
                    )
                if not db_password:
                    raise ToolProviderCredentialValidationError(
                        "Doris database password is required"
                    )
                if not db_name:
                    raise ToolProviderCredentialValidationError(
                        "Doris database name is required"
                    )
            else:
                # 其他数据库类型需要完整的连接信息
                if not db_host:
                    raise ToolProviderCredentialValidationError(
                        "Database host is required"
                    )

                if not db_user:
                    raise ToolProviderCredentialValidationError(
                        "Database user is required"
                    )

                if not db_password:
                    raise ToolProviderCredentialValidationError(
                        "Database password is required"
                    )

                if not db_name:
                    raise ToolProviderCredentialValidationError(
                        "Database name is required"
                    )

            self._build_schema_rag(credentials)
            # 凭据验证成功后，根据build_rag参数决定是否构建schema知识库
            # if build_rag:
            #     self._build_schema_rag(credentials)
            # else:
            #     # 记录跳过构建的信息
            #     logging.info("🚫 build_rag参数为False，跳过Schema RAG构建")
        except ToolProviderCredentialValidationError:
            raise
        except Exception as e:
            logging.error(f"❌ Provider凭据校验失败: {e}")
            raise ToolProviderCredentialValidationError(str(e)) from e

    def _build_schema_rag(self, credentials: dict[str, Any]) -> None:
        """
        Build schema RAG using the provided credentials
        """
        try:

            # 创建数据库配置
            db_type = credentials.get("db_type")
            db_port = self._parse_db_port(credentials)


            if db_type == "doris":
                db_config = DatabaseConfig(
                    type=db_type,
                    host=credentials.get("db_host"),
                    port=db_port,
                    user=credentials.get("db_user"),
                    password=credentials.get("db_password"),
                    database=credentials.get("db_name"),
                )
            else:
                db_config = DatabaseConfig(
                    type=db_type,
                    host=credentials.get("db_host"),
                    port=db_port,
                    user=credentials.get("db_user"),
                    password=credentials.get("db_password"),
                    database=credentials.get("db_name"),
                )

            # 创建日志配置
            logger_config = LoggerConfig(
                log_level="INFO"
            )
            logger = logging.getLogger(__name__)
            logger.setLevel(logging.INFO)
            logger.addHandler(plugin_logger_handler)
            
            # 创建Dify集成配置
            dify_config = DifyUploadConfig(
                api_key=credentials.get("dataset_api_key"),
                base_url=credentials.get("api_uri"),
                indexing_technique="high_quality",
                permission="all_team_members",
                process_mode="custom",
                max_tokens=4000,
            )

            # 解析表名参数
            tables_name = credentials.get("tables_name", "")
            include_tables = None
            if tables_name and tables_name.strip():
                include_tables = [table.strip() for table in tables_name.split(",") if table.strip()]
                logging.info(f"📋 指定构建以下表的RAG: {include_tables}")
            else:
                logging.info("📋 将构建所有表的RAG")

            # 创建构建器实例
            builder = SchemaRAGBuilder(db_config, logger_config, dify_config, include_tables)

            try:
                schema_content = builder.generate_dictionary()

                # 记录成功信息
                table_count = schema_content.count("#") if schema_content else 0
                logging.info(f"📊 数据字典生成成功！包含 {table_count} 个表")

                # 上传到 Dify 知识库
                dataset_name = f"{db_config.database}_schema"
                builder.upload_text_to_dify(dataset_name, schema_content)
                logging.info("☁️ 已成功上传到 Dify 知识库")

            except Exception as e:
                logging.error(f"❌ Schema RAG构建失败: {e}")
                raise ValueError(f"Schema RAG构建失败: {str(e)}")
            finally:
                builder.close()

        except Exception as e:
            logging.error(f"❌ 配置验证或构建过程中发生错误: {e}")
            raise ValueError(f"配置验证或构建过程中发生错误: {str(e)}")

    def get_tools(self):
        """
        Return available tools
        """
        return [Text2SQLTool, SQLExecuterTool]
