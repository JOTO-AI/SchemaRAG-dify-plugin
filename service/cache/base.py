"""
缓存抽象基类 - 定义缓存接口和管理器

该模块提供了缓存系统的核心抽象，包括：
- CacheBackend: 缓存后端的抽象接口
- CacheManager: 缓存管理器，提供全局访问点
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Generic, TypeVar
import logging

K = TypeVar('K')  # 键类型
V = TypeVar('V')  # 值类型


class CacheBackend(ABC, Generic[K, V]):
    """缓存后端抽象基类，定义了缓存操作的标准接口"""
    
    @abstractmethod
    def get(self, key: K) -> Optional[V]:
        """
        从缓存获取值
        
        参数:
            key: 缓存键
            
        返回:
            缓存的值，如果不存在或已过期则返回None
        """
        pass
    
    @abstractmethod
    def set(self, key: K, value: V, ttl: Optional[int] = None) -> None:
        """
        设置缓存值
        
        参数:
            key: 缓存键
            value: 要缓存的值
            ttl: 可选的过期时间（秒），None表示永不过期
        """
        pass
    
    @abstractmethod
    def delete(self, key: K) -> bool:
        """
        删除缓存项
        
        参数:
            key: 缓存键
            
        返回:
            是否成功删除
        """
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """清空所有缓存"""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        返回:
            包含缓存统计数据的字典
        """
        pass


class CacheManager:
    """
    缓存管理器 - 提供全局缓存访问点
    
    使用单例模式管理多个命名缓存实例，支持：
    - 命名缓存实例管理
    - 缓存命中统计
    - 统一的缓存操作接口
    """
    
    _instances: Dict[str, 'CacheManager'] = {}
    _logger = logging.getLogger(__name__)
    
    @classmethod
    def get_instance(cls, name: str = "default") -> 'CacheManager':
        """
        获取或创建命名缓存实例
        
        参数:
            name: 缓存实例名称
            
        返回:
            缓存管理器实例
        """
        if name not in cls._instances:
            from .memory import LRUCache
            cls._instances[name] = CacheManager(name)
            # 自动为新实例设置默认后端
            cls._instances[name].set_backend(LRUCache(max_size=100))
            cls._logger.info(f"创建新的缓存管理器实例: {name}，使用默认LRU后端")
        return cls._instances[name]
    
    @classmethod
    def get_all_instances(cls) -> Dict[str, 'CacheManager']:
        """
        获取所有缓存管理器实例
        
        返回:
            包含所有缓存管理器实例的字典
        """
        return cls._instances.copy()
    
    def __init__(self, name: str):
        """
        初始化缓存管理器
        
        参数:
            name: 缓存实例名称
        """
        self.name = name
        self._backend: Optional[CacheBackend] = None
        self.hit_count = 0
        self.miss_count = 0
    
    def set_backend(self, backend: CacheBackend) -> None:
        """
        设置缓存后端
        
        参数:
            backend: 缓存后端实例
        """
        self._backend = backend
        self._logger.info(f"缓存管理器 {self.name} 设置后端: {backend.__class__.__name__}")
    
    def get(self, key: Any) -> Optional[Any]:
        """
        获取缓存值，并记录命中统计
        
        参数:
            key: 缓存键
            
        返回:
            缓存的值，如果不存在或已过期则返回None
        """
        if not self._backend:
            self._logger.warning(f"缓存管理器 {self.name} 未设置后端")
            return None
            
        result = self._backend.get(key)
        if result is not None:
            self.hit_count += 1
            self._logger.debug(f"缓存命中: {self.name}:{key}")
        else:
            self.miss_count += 1
            self._logger.debug(f"缓存未命中: {self.name}:{key}")
        
        return result
    
    def set(self, key: Any, value: Any, ttl: Optional[int] = None) -> None:
        """
        设置缓存值
        
        参数:
            key: 缓存键
            value: 要缓存的值
            ttl: 可选的过期时间（秒）
        """
        if self._backend:
            self._backend.set(key, value, ttl)
            self._logger.debug(f"设置缓存: {self.name}:{key}, TTL={ttl}")
        else:
            self._logger.warning(f"缓存管理器 {self.name} 未设置后端，无法设置缓存")
    
    def delete(self, key: Any) -> bool:
        """
        删除缓存项
        
        参数:
            key: 缓存键
            
        返回:
            是否成功删除
        """
        if self._backend:
            result = self._backend.delete(key)
            if result:
                self._logger.debug(f"删除缓存: {self.name}:{key}")
            return result
        return False
    
    def clear(self) -> None:
        """清空缓存"""
        if self._backend:
            self._backend.clear()
            self._logger.info(f"清空缓存: {self.name}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        返回:
            包含缓存统计数据的字典，包括命中率、命中次数等
        """
        total = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total if total > 0 else 0
        
        stats = {
            "name": self.name,
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "total_requests": total,
            "hit_rate": round(hit_rate * 100, 2)  # 百分比
        }
        
        if self._backend:
            stats.update(self._backend.get_stats())
            
        return stats
    
    def reset_stats(self) -> None:
        """重置统计信息"""
        self.hit_count = 0
        self.miss_count = 0
        self._logger.info(f"重置缓存统计: {self.name}")
