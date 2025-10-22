"""
内存缓存实现 - 基于LRU策略的内存缓存

该模块提供了高效的内存缓存实现，特点：
- LRU（最近最少使用）淘汰策略
- 支持TTL过期时间
- 自动清理过期项
- 内存占用可控
"""

import time
from typing import Any, Dict, Optional, Tuple
from collections import OrderedDict
import logging

from .base import CacheBackend


class LRUCache(CacheBackend):
    """
    基于LRU策略的内存缓存实现
    
    使用OrderedDict保持访问顺序，实现高效的LRU淘汰。
    每个缓存项存储格式: (value, expire_time)
    """
    
    def __init__(self, max_size: int = 100):
        """
        初始化LRU缓存
        
        参数:
            max_size: 最大缓存项数量，默认100
        """
        if max_size <= 0:
            raise ValueError("max_size必须大于0")
            
        self.max_size = max_size
        self.cache: OrderedDict[Any, Tuple[Any, Optional[float]]] = OrderedDict()
        self._logger = logging.getLogger(__name__)
        
        self._logger.info(f"初始化LRU缓存，最大容量: {max_size}")
    
    def get(self, key: Any) -> Optional[Any]:
        """
        获取缓存项，如存在且未过期则返回
        
        参数:
            key: 缓存键
            
        返回:
            缓存的值，如果不存在或已过期则返回None
        """
        if key not in self.cache:
            return None
            
        value, expire_time = self.cache[key]
        
        # 检查是否过期
        if expire_time is not None and time.time() >= expire_time:
            # 已过期，删除并返回None
            self.delete(key)
            self._logger.debug(f"缓存项已过期: {key}")
            return None
        
        # 更新LRU顺序（移到末尾表示最近使用）
        self.cache.move_to_end(key)
        return value
    
    def set(self, key: Any, value: Any, ttl: Optional[int] = None) -> None:
        """
        设置缓存项，可选TTL（秒）
        
        参数:
            key: 缓存键
            value: 要缓存的值
            ttl: 可选的过期时间（秒），None表示永不过期
        """
        # 计算过期时间
        expire_time = None if ttl is None else time.time() + ttl
        
        # 如果键已存在，直接更新
        if key in self.cache:
            self.cache[key] = (value, expire_time)
            self.cache.move_to_end(key)
            self._logger.debug(f"更新缓存项: {key}")
            return
        
        # 如果缓存已满，移除最久未使用的项（第一项）
        if len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            self.delete(oldest_key)
            self._logger.debug(f"缓存已满，淘汰最久未使用项: {oldest_key}")
        
        # 添加新项
        self.cache[key] = (value, expire_time)
        self.cache.move_to_end(key)
        self._logger.debug(f"添加新缓存项: {key}, TTL={ttl}")
    
    def delete(self, key: Any) -> bool:
        """
        删除缓存项
        
        参数:
            key: 缓存键
            
        返回:
            是否成功删除
        """
        if key in self.cache:
            del self.cache[key]
            self._logger.debug(f"删除缓存项: {key}")
            return True
        return False
    
    def clear(self) -> None:
        """清空所有缓存"""
        count = len(self.cache)
        self.cache.clear()
        self._logger.info(f"清空缓存，删除 {count} 个项")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        返回:
            包含缓存统计数据的字典
        """
        # 计算有效缓存项数量（排除已过期项）
        current_time = time.time()
        valid_items = 0
        expired_items = 0
        
        for value, expire_time in self.cache.values():
            if expire_time is None or expire_time > current_time:
                valid_items += 1
            else:
                expired_items += 1
        
        # 计算内存使用估算（粗略估计）
        memory_estimate = sum(
            self._estimate_size(key) + self._estimate_size(value)
            for key, (value, _) in self.cache.items()
        )
        
        return {
            "backend_type": "lru_memory",
            "max_size": self.max_size,
            "current_size": len(self.cache),
            "valid_items": valid_items,
            "expired_items": expired_items,
            "usage_ratio": round(len(self.cache) / self.max_size * 100, 2),
            "memory_estimate_bytes": memory_estimate
        }
    
    def _estimate_size(self, obj: Any) -> int:
        """
        粗略估算对象大小（字节）
        
        参数:
            obj: 要估算的对象
            
        返回:
            估算的字节数
        """
        try:
            import sys
            return sys.getsizeof(obj)
        except Exception:
            # 如果无法获取大小，返回默认值
            return 128
    
    def cleanup_expired(self) -> int:
        """
        清理所有已过期的缓存项
        
        返回:
            清理的项数
        """
        current_time = time.time()
        expired_keys = [
            key for key, (_, expire_time) in self.cache.items()
            if expire_time is not None and expire_time <= current_time
        ]
        
        for key in expired_keys:
            self.delete(key)
        
        if expired_keys:
            self._logger.info(f"清理了 {len(expired_keys)} 个过期缓存项")
        
        return len(expired_keys)


class TTLCache(CacheBackend):
    """
    基于TTL的简单缓存实现
    
    所有缓存项使用相同的TTL，适用于生命周期一致的场景。
    """
    
    def __init__(self, max_size: int = 100, default_ttl: int = 3600):
        """
        初始化TTL缓存
        
        参数:
            max_size: 最大缓存项数量
            default_ttl: 默认过期时间（秒）
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[Any, Tuple[Any, float]] = {}
        self._logger = logging.getLogger(__name__)
        
        self._logger.info(f"初始化TTL缓存，最大容量: {max_size}, 默认TTL: {default_ttl}秒")
    
    def get(self, key: Any) -> Optional[Any]:
        """获取缓存项，如存在且未过期则返回"""
        if key not in self.cache:
            return None
            
        value, expire_time = self.cache[key]
        
        # 检查是否过期
        if time.time() >= expire_time:
            self.delete(key)
            return None
        
        return value
    
    def set(self, key: Any, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存项"""
        if ttl is None:
            ttl = self.default_ttl
        
        expire_time = time.time() + ttl
        
        # 如果缓存已满，随机删除一项（简单实现）
        if len(self.cache) >= self.max_size and key not in self.cache:
            # 删除第一个过期项，如果没有过期项则删除第一项
            for k, (_, exp_time) in list(self.cache.items()):
                if time.time() >= exp_time:
                    self.delete(k)
                    break
            else:
                # 没有过期项，删除第一项
                first_key = next(iter(self.cache))
                self.delete(first_key)
        
        self.cache[key] = (value, expire_time)
    
    def delete(self, key: Any) -> bool:
        """删除缓存项"""
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    def clear(self) -> None:
        """清空缓存"""
        self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        current_time = time.time()
        valid_items = sum(
            1 for _, expire_time in self.cache.values()
            if expire_time > current_time
        )
        
        return {
            "backend_type": "ttl_memory",
            "max_size": self.max_size,
            "current_size": len(self.cache),
            "valid_items": valid_items,
            "default_ttl": self.default_ttl
        }
