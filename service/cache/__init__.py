"""
通用缓存模块 - 提供灵活、可扩展的缓存解决方案

该模块提供了一个通用的缓存架构，可以轻松集成到项目的各个工具中。
主要特性：
- 基于LRU策略的内存缓存
- 支持TTL（过期时间）
- 装饰器模式简化缓存应用
- 统一的缓存管理和统计
- 易于扩展到其他缓存后端（如Redis）
"""

from .base import CacheManager, CacheBackend
from .memory import LRUCache, TTLCache
from .decorators import cacheable
from .config import CacheConfig
from .utils import normalize_query, generate_hash_key, create_cache_key_from_dict

__all__ = [
    'CacheManager', 'CacheBackend', 'LRUCache', 'TTLCache',
    'cacheable', 'CacheConfig',
    'normalize_query', 'generate_hash_key', 'create_cache_key_from_dict'
]

# 提供一个方便的初始化函数
def initialize_cache(config=None):
    """
    初始化缓存系统
    
    参数:
        config: 可选的缓存配置字典，如果为None则使用默认配置
    """
    CacheConfig.initialize_caches(config)

# 初始化默认缓存
initialize_cache()
