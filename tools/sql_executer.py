import sys
import os
from collections.abc import Generator
from collections import OrderedDict
from typing import Any, Dict, List, Optional
import re
import logging
import hashlib

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)  # 添加上级目录到路径中

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from service.database_service import DatabaseService


class PerformanceConfig:
    """性能配置类，统一管理性能相关参数"""

    MAX_RESULT_ROWS = 10000  # 最大结果行数
    QUERY_TIMEOUT = 30  # 查询超时时间（秒）
    DECIMAL_PLACES = 2  # 小数位数
    CACHE_MAX_SIZE = 5  # 数据库连接缓存大小
    ENABLE_PERFORMANCE_LOG = True  # 是否启用性能日志


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

    # 类级别的服务实例缓存 - 使用 OrderedDict 实现 LRU
    _db_service_cache = OrderedDict()
    _cache_max_size = PerformanceConfig.CACHE_MAX_SIZE

    # 性能和安全相关常量
    MAX_RESULT_ROWS = PerformanceConfig.MAX_RESULT_ROWS  # 最大结果行数
    QUERY_TIMEOUT = PerformanceConfig.QUERY_TIMEOUT  # 查询超时时间（秒）
    DECIMAL_PLACES = PerformanceConfig.DECIMAL_PLACES  # 小数位数

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._db_service = None
        self._db_config = None
        self._config_validated = False
        self.logger = logging.getLogger(__name__)

        # 延迟初始化配置
        self._initialize_config()

    def _initialize_config(self):
        """初始化并验证数据库配置"""
        try:
            credentials = self.runtime.credentials
            self._db_config = {
                "db_type": credentials.get("db_type"),
                "db_host": credentials.get("db_host"),
                "db_port": self._safe_port_conversion(credentials.get("db_port")),
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

    def _safe_port_conversion(self, port_value) -> Optional[int]:
        """安全地转换端口号"""
        if port_value is None:
            return None
        try:
            return int(port_value)
        except (ValueError, TypeError):
            self.logger.warning(f"无效的端口号: {port_value}")
            return None

    @property
    def db_service(self):
        """延迟初始化的数据库服务实例，使用 LRU 缓存"""
        if self._db_service is None:
            # 创建更稳定的配置哈希键
            config_str = f"{self._db_config['db_type']}|{self._db_config['db_host']}|{self._db_config['db_port']}|{self._db_config['db_name']}|{self._db_config['db_user']}"
            config_key = hashlib.md5(config_str.encode()).hexdigest()[:16]

            # LRU 缓存逻辑
            if config_key in self._db_service_cache:
                # 移动到末尾（最近使用）
                self._db_service_cache.move_to_end(config_key)
                self._db_service = self._db_service_cache[config_key]
            else:
                # 如果缓存已满，删除最旧的条目
                if len(self._db_service_cache) >= self._cache_max_size:
                    self._db_service_cache.popitem(last=False)

                # 创建新的服务实例
                new_service = DatabaseService()
                self._db_service_cache[config_key] = new_service
                self._db_service = new_service

        return self._db_service

    @classmethod
    def clear_cache(cls):
        """清理服务缓存，释放资源"""
        cls._db_service_cache.clear()

    @classmethod
    def get_cache_size(cls) -> int:
        """获取当前缓存大小"""
        return len(cls._db_service_cache)

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
        sql_query, output_format, error_msg = self._validate_parameters(tool_parameters)
        if error_msg:
            yield self.create_text_message(f"错误: {error_msg}")
            return

        try:
            # 执行查询前的安全检查
            cleaned_sql = self._clean_and_validate_sql(sql_query)
            if not cleaned_sql:
                yield self.create_text_message("错误: 无效的SQL查询")
                return

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
            if result_count > self.MAX_RESULT_ROWS:
                yield self.create_text_message(
                    f"警告: 查询返回了 {result_count} 行数据，结果已截断到 {self.MAX_RESULT_ROWS} 行"
                )
                results = results[: self.MAX_RESULT_ROWS]

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
            yield self.create_text_message(f"输入错误: {str(e)}")
        except ConnectionError as e:
            # 数据库连接错误
            yield self.create_text_message(f"数据库连接错误: {str(e)}")
        except Exception as e:
            # 其他未预期的错误
            self.logger.error(f"SQL执行异常: {str(e)}")
            yield self.create_text_message(f"SQL执行时发生错误: {str(e)}")

    def _validate_parameters(
        self, tool_parameters: dict[str, Any]
    ) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """验证工具参数并返回处理后的值"""
        # 验证SQL查询
        sql_query = tool_parameters.get("sql")
        if not sql_query or not sql_query.strip():
            return None, None, "SQL查询不能为空"

        # 验证输出格式
        output_format = tool_parameters.get("output_format", "json")
        if output_format not in ["json", "md"]:
            return None, None, "输出格式只支持 'json' 或 'md'"

        return sql_query.strip(), output_format, None

    def _clean_and_validate_sql(self, sql_query: str) -> Optional[str]:
        """清理和验证SQL查询，提高安全性和性能"""
        if not sql_query:
            return None

        try:
            # 使用正则表达式清理markdown格式（优化版本）
            markdown_pattern = re.compile(
                r"```(?:sql)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE
            )
            match = markdown_pattern.search(sql_query)

            if match:
                cleaned_sql = match.group(1).strip()
            else:
                cleaned_sql = sql_query.strip()

            if not cleaned_sql:
                return None

            # 移除多余的空白字符和换行符
            cleaned_sql = re.sub(r"\s+", " ", cleaned_sql).strip()

            # 安全检查：只允许SELECT语句（大小写不敏感）
            sql_lower = cleaned_sql.lower()
            if not sql_lower.startswith("select"):
                raise ValueError("出于安全考虑，只允许执行SELECT查询")

            # 额外安全检查：禁止危险关键字
            dangerous_keywords = [
                "drop",
                "delete",
                "update",
                "insert",
                "create",
                "alter",
                "truncate",
                "exec",
                "execute",
                "sp_",
                "xp_",
                "--",
                "/*",
            ]

            for keyword in dangerous_keywords:
                if keyword in sql_lower:
                    raise ValueError(f"SQL查询包含被禁止的关键字: {keyword}")

            return cleaned_sql

        except ValueError:
            # 重新抛出验证错误
            raise
        except Exception as e:
            self.logger.warning(f"SQL清理失败: {str(e)}")
            return None

    def _format_numeric_values(self, results: List[Dict]) -> List[Dict]:
        """格式化数值，避免科学计数法，保留指定小数位数"""
        if not results:
            return results

        formatted_results = []
        for row in results:
            formatted_row = {}
            for key, value in row.items():
                formatted_row[key] = self._format_single_value(value)
            formatted_results.append(formatted_row)

        self.logger.debug(f"数值格式化完成，处理了 {len(formatted_results)} 行数据")
        return formatted_results

    def _format_single_value(self, value) -> Any:
        """格式化单个值，优化性能和逻辑"""
        # 快速处理 None 和布尔值
        if value is None or isinstance(value, bool):
            return value

        # 处理字符串和其他非数值类型
        if not isinstance(value, (int, float)):
            return value

        try:
            # 处理整数
            if isinstance(value, int):
                return str(value)

            # 处理浮点数（包括 NaN 和无穷大）
            if isinstance(value, float):
                # 检查是否为有效数值
                if not (value == value):  # 检查 NaN，比 pd.isna() 更快
                    return None

                # 检查无穷大
                if abs(value) == float("inf"):
                    return str(value)

                # 检查是否为整数值（如 1.0, 2.0）
                if value.is_integer():
                    return str(int(value))  # 1.0 显示为 "1" 而不是 "1.00"
                else:
                    # 浮点数保留指定小数位数，避免科学计数法
                    return f"{value:.{self.DECIMAL_PLACES}f}"

            # 其他数值类型的安全处理
            return str(value)

        except (ValueError, OverflowError, TypeError, AttributeError):
            # 处理异常情况，保留原始值的字符串形式
            return str(value) if value is not None else None
