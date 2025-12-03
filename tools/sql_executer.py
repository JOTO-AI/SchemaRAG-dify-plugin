import sys
import os
from collections.abc import Generator
from typing import Any, Dict, List, Optional
import re
import logging

from utils import (
    _clean_and_validate_sql,
    PerformanceConfig,
    safe_port_conversion,
    format_numeric_values,
    create_config_hash,
    LRUCache
)

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)  # 添加上级目录到路径中

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from service.database_service import DatabaseService
from dify_plugin.config.logger_format import plugin_logger_handler
from tools.parameter_validator import validate_and_extract_sql_executer_parameters


class SQLExecuterTool(Tool):
    """
    SQL Executer Tool with optimized performance

    性能优化包括:
    1. LRU缓存机制：使用OrderedDict实现数据库连接缓存
    2. 数值格式化优化：减少冗余检查，提高处理速度
    3. SQL安全验证增强：添加更多安全检查，防止SQL注入
    4. 内存使用优化：早期结果检查，避免处理空结果集
    5. 执行时间监控：记录查询执行时间
    6. 配置哈希优化：使用MD5哈希生成稳定的缓存键
    """

    # 类级别的服务实例缓存 - 使用LRUCache
    _db_service_cache = LRUCache(max_size=PerformanceConfig.CACHE_MAX_SIZE)

    # 性能和安全相关常量
    QUERY_TIMEOUT = PerformanceConfig.QUERY_TIMEOUT  # 查询超时时间（秒）
    DECIMAL_PLACES = PerformanceConfig.DECIMAL_PLACES  # 小数位数

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._db_service = None
        self._db_config = None
        self._config_validated = False
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(plugin_logger_handler)

        # 延迟初始化配置
        self._initialize_config()

    def _initialize_config(self):
        """初始化并验证数据库配置"""
        try:
            credentials = self.runtime.credentials
            self._db_config = {
                "db_type": credentials.get("db_type"),
                "db_host": credentials.get("db_host"),
                "db_port": safe_port_conversion(credentials.get("db_port"), self.logger),
                "db_user": credentials.get("db_user"),
                "db_password": credentials.get("db_password"),
                "db_name": credentials.get("db_name"),
            }
            
            # 验证配置完整性
            self._config_validated = all(
                value is not None for value in self._db_config.values()
            )

        except Exception as e:
            self.logger.error(f"配置初始化失败: {str(e)}")
            self._config_validated = False

    @property
    def db_service(self):
        """延迟初始化的数据库服务实例，使用 LRU 缓存"""
        if self._db_service is None:
            # 创建配置哈希键
            config_key = create_config_hash(self._db_config)

            # LRU 缓存逻辑
            cached_service = self._db_service_cache.get(config_key)
            if cached_service:
                self._db_service = cached_service
            else:
                # 创建新的服务实例并缓存
                new_service = DatabaseService()
                self._db_service_cache.put(config_key, new_service)
                self._db_service = new_service

        return self._db_service

    @classmethod
    def clear_cache(cls):
        """清理服务缓存，释放资源"""
        cls._db_service_cache.clear()

    @classmethod
    def get_cache_size(cls) -> int:
        """获取当前缓存大小"""
        return cls._db_service_cache.size()

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        """
        Execute SQL queries and return results in specified format.
        """
        # 早期验证配置
        if not self._config_validated:
            yield self.create_text_message(
                "错误: 数据库配置不完整或无效，请检查provider配置"
            )
            return

        # 验证参数
        sql_query, output_format, max_rows, error_msg = validate_and_extract_sql_executer_parameters(
            tool_parameters,
            default_max_rows=500,
            logger=self.logger
        )
        if error_msg:
            self.logger.error(f"错误: {error_msg}")
            raise ValueError(error_msg)

        try:
            # 执行查询前的安全检查
            cleaned_sql = _clean_and_validate_sql(sql_query)
            if not cleaned_sql:
                self.logger.error("错误: 无效的SQL查询")
                raise ValueError("无效的SQL查询")

            # 记录查询开始时间
            import time

            start_time = time.time()

            # 执行查询
            self.logger.info(f"执行SQL查询: {cleaned_sql[:100]}...")
            results, columns = self.db_service.execute_query(
                self._db_config["db_type"],
                self._db_config["db_host"],
                self._db_config["db_port"],
                self._db_config["db_user"],
                self._db_config["db_password"],
                self._db_config["db_name"],
                cleaned_sql,
            )

            # 记录执行时间
            execution_time = time.time() - start_time
            self.logger.info(f"SQL查询执行完成，耗时: {execution_time:.3f}秒")

            # 早期检查结果
            result_count = len(results)
            if result_count == 0:
                yield self.create_text_message("查询执行成功，但没有返回数据")
                return

            # 检查结果大小，防止内存问题
            if result_count > max_rows:
                self.logger.warning(
                    f"警告: 查询返回了 {result_count} 行数据，结果已截断到 {max_rows} 行"
                )
                results = results[:max_rows]

            # 只有在有数据时才进行格式化
            if results:
                # 格式化数值，避免科学计数法
                formatted_results = self._format_numeric_values(results)

                # 格式化输出
                formatted_output = self.db_service._format_output(
                    formatted_results, columns, output_format
                )
                yield self.create_text_message(text=formatted_output)

            self.logger.info(f"SQL查询结果处理完成，返回 {len(results)} 行数据")

        except ValueError as e:
            # 输入验证错误
            self.logger.error(f"输入错误: {str(e)}")
            raise ValueError(f"输入错误: {str(e)}")

        except ConnectionError as e:
            # 数据库连接错误
            self.logger.error(f"数据库连接错误: {str(e)}")
            raise ConnectionError(f"数据库连接错误: {str(e)}")
        except Exception as e:
            # 其他未预期的错误
            self.logger.error(f"SQL执行异常: {str(e)}")
            raise ValueError(f"SQL执行异常: {str(e)}")

    def _format_numeric_values(self, results: List[Dict]) -> List[Dict]:
        """格式化数值，避免科学计数法，保留指定小数位数"""
        return format_numeric_values(results, self.DECIMAL_PLACES, self.logger)
