import os
from typing import Any
import sys
import logging

from tools.text2data import Text2DataTool

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)  # 添加上级目录到路径中

from dify_plugin import ToolProvider
from tools.text2sql import Text2SQLTool
from tools.sql_executer import SQLExecuterTool
from config import DatabaseConfig, LoggerConfig, DifyUploadConfig
from service.schema_builder import SchemaRAGBuilder


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
        }
        return port_mapping.get(db_type, 3306)

    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        """
        Validate the credentials and build schema RAG
        """
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
            raise ValueError("API URI is required")

        if not dataset_api_key:
            raise ValueError("Dataset API key is required")

        # 验证数据库相关参数
        if not db_type:
            raise ValueError("Database type is required")

        # SQLite 只需要数据库名称（文件路径）
        if db_type == "sqlite":
            if not db_name:
                raise ValueError("Database name (file path) is required for SQLite")
        else:
            # 其他数据库类型需要完整的连接信息
            if not db_host:
                raise ValueError("Database host is required")

            if not db_user:
                raise ValueError("Database user is required")

            if not db_password:
                raise ValueError("Database password is required")

            if not db_name:
                raise ValueError("Database name is required")

        self._build_schema_rag(credentials)
        # 凭据验证成功后，根据build_rag参数决定是否构建schema知识库
        # if build_rag:
        #     self._build_schema_rag(credentials)
        # else:
        #     # 记录跳过构建的信息
        #     logging.info("🚫 build_rag参数为False，跳过Schema RAG构建")

    def _build_schema_rag(self, credentials: dict[str, Any]) -> None:
        """
        Build schema RAG using the provided credentials
        """
        try:
            # 获取项目根目录
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

            # 确保logs目录存在
            logs_dir = os.path.join(project_root, "logs")
            os.makedirs(logs_dir, exist_ok=True)

            # 创建数据库配置
            db_type = credentials.get("db_type")
            default_port = self._get_default_port(db_type)
            db_port = credentials.get("db_port")

            # 如果用户没有提供端口或端口为空，使用默认端口
            if not db_port:
                port = default_port
            else:
                port = int(db_port)

            # 对于 SQLite，使用默认值处理缺失的字段
            if db_type == "sqlite":
                db_config = DatabaseConfig(
                    type=db_type,
                    host="localhost",  # SQLite 不使用，但为了兼容性设置默认值
                    port=0,  # SQLite 不使用端口
                    user="",  # SQLite 不需要用户名
                    password="",  # SQLite 不需要密码
                    database=credentials.get("db_name"),  # SQLite 的文件路径
                )
            else:
                db_config = DatabaseConfig(
                    type=db_type,
                    host=credentials.get("db_host"),
                    port=port,
                    user=credentials.get("db_user"),
                    password=credentials.get("db_password"),
                    database=credentials.get("db_name"),
                )

            # 创建日志配置
            logger_config = LoggerConfig(
                log_level="INFO", log_file=os.path.join(logs_dir, "schema_builder.log")
            )

            # 创建Dify集成配置
            dify_config = DifyUploadConfig(
                api_key=credentials.get("dataset_api_key"),
                base_url=credentials.get("api_uri"),
                indexing_technique="high_quality",
                permission="all_team_members",
                process_mode="custom",
                max_tokens=1000,
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
                # 确保output目录存在
                output_dir = os.path.join(project_root, "output")
                os.makedirs(output_dir, exist_ok=True)

                # 生成数据字典
                # schema_file_path = os.path.join(
                #     output_dir, f"{db_config.database}_schema.md"
                # )
                schema_content = builder.generate_dictionary()
                # logging.info(f"📄 生成的Schema内容: {schema_content} ")

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
        return [Text2SQLTool, SQLExecuterTool, Text2DataTool]
