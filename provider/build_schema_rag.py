import os
from typing import Any
import sys
import logging

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

    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        """
        Validate the credentials and build schema RAG
        """
        # 验证必要的凭据
        api_uri = credentials.get("api_uri")
        dataset_api_key = credentials.get("dataset_api_key")
        db_type = credentials.get("db_type")
        db_host = credentials.get("db_host")
        db_port = credentials.get("db_port")
        db_user = credentials.get("db_user")
        db_password = credentials.get("db_password")
        db_name = credentials.get("db_name")

        # 验证API相关参数
        if not api_uri:
            raise ValueError("API URI is required")

        if not dataset_api_key:
            raise ValueError("Dataset API key is required")

        # 验证数据库相关参数
        if not db_type:
            raise ValueError("Database type is required")
        
        if not db_host:
            raise ValueError("Database host is required")
            
        if not db_port:
            raise ValueError("Database port is required")
            
        if not db_user:
            raise ValueError("Database user is required")
            
        if not db_password:
            raise ValueError("Database password is required")
            
        if not db_name:
            raise ValueError("Database name is required")

        # 凭据验证成功后，自动构建schema知识库
        self._build_schema_rag(credentials)

    def _build_schema_rag(self, credentials: dict[str, Any]) -> None:
        """
        Build schema RAG using the provided credentials
        """
        try:
            # 获取项目根目录
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # 确保logs目录存在
            logs_dir = os.path.join(project_root, 'logs')
            os.makedirs(logs_dir, exist_ok=True)
            
            # 创建数据库配置
            db_config = DatabaseConfig(
                type=credentials.get("db_type"),
                host=credentials.get("db_host"),
                port=int(credentials.get("db_port", 3306)),
                user=credentials.get("db_user"),
                password=credentials.get("db_password"),
                database=credentials.get("db_name")
            )

            # 创建日志配置
            logger_config = LoggerConfig(
                log_level='INFO',
                log_file=os.path.join(logs_dir, 'schema_builder.log')
            )

            # 创建Dify集成配置
            dify_config = DifyUploadConfig(
                api_key=credentials.get("dataset_api_key"),
                base_url=credentials.get("api_uri"),
                indexing_technique="high_quality",
                permission="all_team_members",
                process_mode="custom",
                max_tokens=1000
            )

            # 创建构建器实例
            builder = SchemaRAGBuilder(db_config, logger_config, dify_config)

            try:
                # 确保output目录存在
                output_dir = os.path.join(project_root, 'output')
                os.makedirs(output_dir, exist_ok=True)
                
                # 生成数据字典
                schema_file_path = os.path.join(output_dir, f'{db_config.database}_schema.md')
                schema_content = builder.generate_dictionary(schema_file_path)
                
                # 记录成功信息
                table_count = schema_content.count("#") if schema_content else 0
                logging.info(f'📊 数据字典生成成功！包含 {table_count} 个表')
                
                # 上传到 Dify 知识库
                dataset_name = f'{db_config.database}_schema'
                builder.upload_text_to_dify(dataset_name, schema_content)
                logging.info('☁️ 已成功上传到 Dify 知识库')
                
            except Exception as e:
                logging.error(f'❌ Schema RAG构建失败: {e}')
                raise ValueError(f"Schema RAG构建失败: {str(e)}")
            finally:
                builder.close()
                
        except Exception as e:
            logging.error(f'❌ 配置验证或构建过程中发生错误: {e}')
            raise ValueError(f"配置验证或构建过程中发生错误: {str(e)}")

    def get_tools(self):
        """
        Return available tools
        """
        return [Text2SQLTool, SQLExecuterTool]
