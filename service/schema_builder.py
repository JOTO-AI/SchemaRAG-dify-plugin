import os
import logging
from typing import Optional
import sys

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)  # 添加上级目录到路径中

from sqlalchemy.engine import Engine
from sqlalchemy import create_engine
from core.m_schema.schema_engine import SchemaEngine
from config import DatabaseConfig, DifyUploadConfig, LoggerConfig
from service.dify_service import DifyUploader
from utils import Logger, read_json, save_raw_text


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
        self.logger_manager = Logger(self.logger_config)
        self.logger = self.logger_manager.get_logger()
        self.engine: Optional[Engine] = create_engine(
            self.db_config.get_connection_string()
        )
        self.uploader: Optional[DifyUploader] = None
        self.schema_engine: Optional[SchemaEngine] = None
        self._initialize_components()

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
            raise RuntimeError("数据库引擎未成功创建，请检查数据库配置")
        try:
            self.schema_engine = SchemaEngine(
                engine=self.engine,
                db_name=self.db_config.database,
            )
            self.logger.info("Schema引擎初始化成功")
        except Exception as e:
            self.logger.error(f"Schema引擎初始化失败: {e}")
            raise RuntimeError("无法初始化Schema引擎，请检查数据库配置")
        if self.dify_config:
            try:
                self.uploader = DifyUploader(self.dify_config, self.logger)
                self.logger.info("Dify上传器初始化成功")
            except ImportError as e:
                self.logger.error(f"Dify组件初始化失败: {e}")
                self.uploader = None

    def generate_dictionary(self, save_path: Optional[str] = None) -> Optional[str]:
        """
        生成数据字典文件。
        :param save_path: 可选，保存路径（支持.json/.txt/.md）
        :return: 数据字典字符串
        """
        if not self.schema_engine:
            self.logger.error("Schema引擎未初始化，无法生成数据字典")
            raise RuntimeError("Schema引擎未初始化，请检查数据库连接")
        self.logger.info("开始生成数据字典...")
        try:
            mschema = self.schema_engine.mschema
            if not mschema:
                self.logger.error("未能获取到数据库schema信息")
                raise RuntimeError("无法获取数据库schema信息，请检查数据库连接")
            mschema_str = mschema.to_mschema()
            if save_path:
                if save_path.endswith(".json"):
                    mschema.save(save_path)
                elif save_path.endswith(".txt") or save_path.endswith(".md"):
                    save_raw_text(save_path, mschema_str)
                logging.info(f"数据字典已保存到: {save_path}")
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
