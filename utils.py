"""
工具模块
"""

import logging
from typing import Optional, Any, Dict, List
from collections import OrderedDict
import hashlib
from config import LoggerConfig

import datetime
import decimal
import re
import json


class PerformanceConfig:
    """性能配置类，统一管理性能相关参数"""

    QUERY_TIMEOUT = 30  # 查询超时时间（秒）
    DECIMAL_PLACES = 2  # 小数位数
    CACHE_MAX_SIZE = 5  # 数据库连接缓存大小
    ENABLE_PERFORMANCE_LOG = True  # 是否启用性能日志


def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def read_text(filename) -> str:
    data = []
    with open(filename, "r", encoding="utf-8") as file:
        for line in file.readlines():
            line = line.strip()
            data.append(line)
    return data


def save_raw_text(filename, content):
    with open(filename, "w", encoding="utf-8") as file:
        file.write(content)


def read_map_file(path):
    data = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f.readlines():
            line = line.strip().split("\t")
            data[line[0]] = line[1].split("、")
            data[line[0]].append(line[0])
    return data


def save_json(target_file, js, indent=4):
    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(js, f, ensure_ascii=False, indent=indent)


def is_email(string):
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    match = re.match(pattern, string)
    if match:
        return True
    else:
        return False


def examples_to_str(examples: list) -> list[str]:
    """
    from examples to a list of str
    """
    values = examples
    for i in range(len(values)):
        if isinstance(values[i], datetime.date):
            values = [values[i]]
            break
        elif isinstance(values[i], datetime.datetime):
            values = [values[i]]
            break
        elif isinstance(values[i], decimal.Decimal):
            values[i] = str(float(values[i]))
        elif is_email(str(values[i])):
            values = []
            break
        elif "http://" in str(values[i]) or "https://" in str(values[i]):
            values = []
            break
        elif values[i] is not None and not isinstance(values[i], str):
            pass
        elif values[i] is not None and ".com" in values[i]:
            pass

    return [str(v) for v in values if v is not None and len(str(v)) > 0]

def _clean_and_validate_sql(sql_query: str) -> Optional[str]:
    """清理和验证SQL查询，使用正则黑名单模式，禁止危险操作"""
    if not sql_query:
        return None

    try:
        # 清理 markdown 格式
        markdown_pattern = re.compile(
            r"```(?:sql)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE
        )
        match = markdown_pattern.search(sql_query)
        cleaned_sql = match.group(1).strip() if match else sql_query.strip()
        if not cleaned_sql:
            return None

        # 移除多余空白
        cleaned_sql = re.sub(r"\s+", " ", cleaned_sql).strip()
        sql_lower = cleaned_sql.lower()

        # 黑名单模式：禁止危险的SQL操作
        dangerous_patterns = [
            r'^\s*(drop|delete|truncate|update|insert|create|alter|grant|revoke)\s+',  # 危险的DDL/DML操作
            r'\b(exec|execute|sp_|xp_)\b',  # 存储过程执行
            r'\b(into\s+outfile|load_file|load\s+data)\b',  # 文件操作
            r'\b(union\s+all\s+select.*into|select.*into)\b',  # SELECT INTO操作
            r';\s*(drop|delete|truncate|update|insert|create|alter)',  # 分号后的危险操作
            r'\b(benchmark|sleep|waitfor|delay)\b',  # 时间延迟函数
            r'@@|information_schema\.(?!columns|tables|schemata)',  # 系统变量和敏感信息模式表
        ]

        # 检查是否包含危险模式
        for pattern in dangerous_patterns:
            if re.search(pattern, sql_lower, re.IGNORECASE):
                raise ValueError(f"检测到危险的SQL操作，查询被拒绝")

        return cleaned_sql

    except ValueError:
        # 重新抛出验证错误
        raise
    except Exception as e:
        return None


def safe_port_conversion(port_value, logger=None) -> Optional[int]:
    """安全地转换端口号
    
    Args:
        port_value: 端口值（可以是字符串、整数或None）
        logger: 可选的日志记录器
        
    Returns:
        转换后的整数端口号，如果无效则返回None
    """
    if port_value is None:
        return None
    try:
        return int(port_value)
    except (ValueError, TypeError):
        if logger:
            logger.warning(f"无效的端口号: {port_value}")
        return None


def format_numeric_values(results: List[Dict], decimal_places: int = 2, logger=None) -> List[Dict]:
    """格式化数值，避免科学计数法，保留指定小数位数
    
    Args:
        results: 查询结果列表
        decimal_places: 小数位数，默认为2
        logger: 可选的日志记录器
        
    Returns:
        格式化后的结果列表
    """
    if not results:
        return results

    formatted_results = []
    for row in results:
        formatted_row = {}
        for key, value in row.items():
            formatted_row[key] = format_single_value(value, decimal_places)
        formatted_results.append(formatted_row)

    if logger:
        logger.debug(f"数值格式化完成，处理了 {len(formatted_results)} 行数据")
    return formatted_results


def format_single_value(value, decimal_places: int = 2) -> Any:
    """格式化单个值，优化性能和逻辑
    
    Args:
        value: 要格式化的值
        decimal_places: 小数位数，默认为2
        
    Returns:
        格式化后的值
    """
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
                return f"{value:.{decimal_places}f}"

        # 其他数值类型的安全处理
        return str(value)

    except (ValueError, OverflowError, TypeError, AttributeError):
        # 处理异常情况，保留原始值的字符串形式
        return str(value) if value is not None else None


def create_config_hash(db_config: Dict[str, Any]) -> str:
    """创建数据库配置的哈希键，用于缓存
    
    Args:
        db_config: 数据库配置字典，包含db_type、host、port、dbname、user等
        
    Returns:
        MD5哈希字符串（16字符）
    """
    config_str = f"{db_config.get('db_type')}|{db_config.get('db_host')}|{db_config.get('db_port')}|{db_config.get('db_name')}|{db_config.get('db_user')}"
    return hashlib.md5(config_str.encode()).hexdigest()[:16]


class LRUCache:
    """LRU缓存实现，用于数据库服务缓存
    
    使用OrderedDict实现简单高效的LRU缓存机制
    """
    
    def __init__(self, max_size: int = 5):
        """初始化LRU缓存
        
        Args:
            max_size: 最大缓存大小，默认为5
        """
        self._cache = OrderedDict()
        self._max_size = max_size
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存项，并移到最近使用位置
        
        Args:
            key: 缓存键
            
        Returns:
            缓存的值，如果不存在则返回None
        """
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None
    
    def put(self, key: str, value: Any) -> None:
        """添加或更新缓存项
        
        Args:
            key: 缓存键
            value: 要缓存的值
        """
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)
        self._cache[key] = value
    
    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
    
    def size(self) -> int:
        """获取当前缓存大小"""
        return len(self._cache)
    
    def contains(self, key: str) -> bool:
        """检查键是否在缓存中"""
        return key in self._cache


class Logger:
    """日志管理器"""

    def __init__(self, config: LoggerConfig):
        self.config = config
        self._setup_logging()

    def _setup_logging(self):
        """设置日志配置"""
        handlers = [logging.StreamHandler()]

        # Only add FileHandler if log_file is not None
        # if self.config.log_file is not None:
        #     handlers.append(logging.FileHandler(self.config.log_file, encoding="utf-8"))

        # 将日志级别转换为大写，以匹配logging模块的常量
        log_level = self.config.log_level.upper()

        logging.basicConfig(
            level=getattr(logging, log_level),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=handlers,
            force=True,
        )
        self.logger = logging.getLogger("dict_generator")

    def get_logger(self) -> logging.Logger:
        """获取日志记录器"""
        return self.logger
