"""
缓存工具函数 - 提供缓存相关的实用工具

该模块包含：
- 查询规范化函数
- 缓存键生成函数
- 其他辅助工具
"""

import re
import hashlib
from typing import Any, List


def normalize_query(query: str, remove_stopwords: bool = True) -> str:
    """
    规范化查询字符串，增加缓存命中率
    
    参数:
        query: 原始查询字符串
        remove_stopwords: 是否移除停用词，默认True
        
    返回:
        规范化后的查询字符串
        
    示例:
        >>> normalize_query("  请 帮我  查询 用户信息  ")
        "用户信息"
        >>> normalize_query("SELECT * FROM users", remove_stopwords=False)
        "select * from users"
    """
    if not query or not isinstance(query, str):
        return ""
    
    # 移除多余空格、转为小写
    normalized = re.sub(r'\s+', ' ', query).lower().strip()
    
    # 移除常见的无意义词
    if remove_stopwords:
        stopwords = [
            "请", "帮我", "查询", "获取", "告诉我", "我想", 
            "能否", "可以", "如何", "怎么", "帮忙"
        ]
        for word in stopwords:
            normalized = normalized.replace(word, "")
        
        # 再次清理空格
        normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return normalized


def generate_hash_key(*args: Any, **kwargs: Any) -> str:
    """
    生成参数的哈希键
    
    将所有位置参数和关键字参数转换为字符串并计算MD5哈希，
    用于生成稳定的缓存键。
    
    参数:
        *args: 位置参数
        **kwargs: 关键字参数
        
    返回:
        MD5哈希值（32位十六进制字符串）
        
    示例:
        >>> generate_hash_key("user", 123, action="query")
        "a1b2c3d4e5f6..."
    """
    # 将所有参数转换为字符串并合并
    # 对kwargs排序以确保相同参数产生相同哈希
    args_str = str(args)
    kwargs_str = str(sorted(kwargs.items()))
    combined = args_str + kwargs_str
    
    # 计算MD5哈希
    return hashlib.md5(combined.encode('utf-8')).hexdigest()


def generate_cache_key(prefix: str, *args: Any, **kwargs: Any) -> str:
    """
    生成带前缀的缓存键
    
    参数:
        prefix: 缓存键前缀
        *args: 位置参数
        **kwargs: 关键字参数
        
    返回:
        格式化的缓存键：prefix:hash
        
    示例:
        >>> generate_cache_key("user", 123, action="query")
        "user:a1b2c3d4e5f6..."
    """
    hash_key = generate_hash_key(*args, **kwargs)
    return f"{prefix}:{hash_key}"


def create_cache_key_from_dict(prefix: str, params: dict) -> str:
    """
    从字典参数创建缓存键
    
    参数:
        prefix: 缓存键前缀
        params: 参数字典
        
    返回:
        缓存键
        
    示例:
        >>> create_cache_key_from_dict("schema", {"dataset_id": "123", "query": "users"})
        "schema:abc123..."
    """
    # 对字典键排序以确保稳定性
    sorted_items = sorted(params.items())
    combined = str(sorted_items)
    hash_key = hashlib.md5(combined.encode('utf-8')).hexdigest()
    return f"{prefix}:{hash_key}"


def sanitize_cache_key(key: str, max_length: int = 250) -> str:
    """
    清理缓存键，移除不安全字符并限制长度
    
    参数:
        key: 原始缓存键
        max_length: 最大长度，默认250
        
    返回:
        清理后的缓存键
    """
    # 移除或替换不安全字符
    sanitized = re.sub(r'[^\w\-:]', '_', key)
    
    # 限制长度，如果超长则使用哈希
    if len(sanitized) > max_length:
        # 保留前缀和后缀，中间用哈希代替
        prefix_len = min(50, max_length // 3)
        suffix_len = min(50, max_length // 3)
        
        prefix = sanitized[:prefix_len]
        suffix = sanitized[-suffix_len:]
        middle_hash = hashlib.md5(sanitized.encode('utf-8')).hexdigest()[:16]
        
        sanitized = f"{prefix}_{middle_hash}_{suffix}"
    
    return sanitized


def estimate_string_size(text: str) -> int:
    """
    估算字符串的内存占用（字节）
    
    参数:
        text: 要估算的字符串
        
    返回:
        估算的字节数
    """
    try:
        # Python 3中字符串使用UTF-8编码
        return len(text.encode('utf-8'))
    except Exception:
        # 粗略估算：假设平均每个字符2字节
        return len(text) * 2


def batch_normalize_queries(queries: List[str]) -> List[str]:
    """
    批量规范化查询字符串
    
    参数:
        queries: 查询字符串列表
        
    返回:
        规范化后的查询字符串列表
    """
    return [normalize_query(q) for q in queries]


def is_cache_key_valid(key: Any) -> bool:
    """
    检查缓存键是否有效
    
    参数:
        key: 缓存键
        
    返回:
        是否有效
    """
    if key is None:
        return False
    
    # 检查是否为字符串或可哈希类型
    try:
        hash(key)
        return True
    except TypeError:
        return False
