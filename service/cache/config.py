"""
缓存配置管理 - 统一管理所有缓存配置

该模块负责：
- 定义默认缓存配置
- 初始化所有缓存实例
- 提供全局缓存统计
"""

from typing import Any, Dict, Optional
import logging

from .base import CacheManager
from .memory import LRUCache, TTLCache


class CacheConfig:
    """
    缓存配置管理类
    
    提供统一的缓存配置和初始化接口
    """
    
    # 默认缓存配置
    DEFAULT_CONFIG = {
        # Schema检索缓存配置
        "schema_cache": {
            "type": "lru",
            "max_size": 100,
            "ttl": 3600  # 1小时
        },
        # SQL生成结果缓存配置
        "sql_cache": {
            "type": "lru",
            "max_size": 50,
            "ttl": 7200  # 2小时
        },
        # 提示词模板缓存配置
        "prompt_cache": {
            "type": "lru",
            "max_size": 20,
            "ttl": 86400  # 24小时
        },
        # 数据集信息缓存配置
        "dataset_info_cache": {
            "type": "ttl",
            "max_size": 50,
            "default_ttl": 3600  # 1小时
        }
    }
    
    _logger = logging.getLogger(__name__)
    _initialized = False
    
    @classmethod
    def initialize_caches(cls, config: Optional[Dict[str, Any]] = None) -> None:
        """
        初始化所有缓存实例
        
        参数:
            config: 缓存配置，如果为None则使用默认配置
        """
        if cls._initialized:
            cls._logger.info("缓存系统已初始化，跳过重复初始化")
            return
        
        if config is None:
            config = cls.DEFAULT_CONFIG
            cls._logger.info("使用默认缓存配置")
        
        cls._logger.info(f"开始初始化 {len(config)} 个缓存实例")
        
        for cache_name, cache_config in config.items():
            try:
                cls._initialize_single_cache(cache_name, cache_config)
            except Exception as e:
                cls._logger.error(f"初始化缓存 {cache_name} 失败: {e}")
        
        cls._initialized = True
        cls._logger.info("缓存系统初始化完成")
    
    @classmethod
    def _initialize_single_cache(cls, cache_name: str, cache_config: Dict[str, Any]) -> None:
        """
        初始化单个缓存实例
        
        参数:
            cache_name: 缓存名称
            cache_config: 缓存配置
        """
        cache_type = cache_config.get("type", "lru")
        max_size = cache_config.get("max_size", 100)
        
        # 创建缓存管理器实例
        cache_manager = CacheManager.get_instance(cache_name)
        
        # 根据类型创建缓存后端
        if cache_type == "lru":
            backend = LRUCache(max_size=max_size)
        elif cache_type == "ttl":
            default_ttl = cache_config.get("default_ttl", 3600)
            backend = TTLCache(max_size=max_size, default_ttl=default_ttl)
        else:
            cls._logger.warning(f"未知的缓存类型 {cache_type}，使用默认LRU缓存")
            backend = LRUCache(max_size=max_size)
        
        # 设置后端
        cache_manager.set_backend(backend)
        cls._logger.info(
            f"缓存 {cache_name} 初始化完成: type={cache_type}, max_size={max_size}"
        )
    
    @classmethod
    def get_all_stats(cls) -> Dict[str, Dict[str, Any]]:
        """
        获取所有缓存的统计信息
        
        返回:
            包含所有缓存统计信息的字典
        """
        stats = {}
        all_instances = CacheManager.get_all_instances()
        
        for cache_name, cache_manager in all_instances.items():
            try:
                stats[cache_name] = cache_manager.get_stats()
            except Exception as e:
                cls._logger.error(f"获取缓存 {cache_name} 统计失败: {e}")
                stats[cache_name] = {"error": str(e)}
        
        return stats
    
    @classmethod
    def clear_all_caches(cls) -> None:
        """清空所有缓存"""
        cls._logger.info("开始清空所有缓存")
        all_instances = CacheManager.get_all_instances()
        
        for cache_name, cache_manager in all_instances.items():
            try:
                cache_manager.clear()
                cls._logger.info(f"清空缓存: {cache_name}")
            except Exception as e:
                cls._logger.error(f"清空缓存 {cache_name} 失败: {e}")
    
    @classmethod
    def reset_all_stats(cls) -> None:
        """重置所有缓存的统计信息"""
        cls._logger.info("开始重置所有缓存统计")
        all_instances = CacheManager.get_all_instances()
        
        for cache_name, cache_manager in all_instances.items():
            try:
                cache_manager.reset_stats()
            except Exception as e:
                cls._logger.error(f"重置缓存 {cache_name} 统计失败: {e}")
    
    @classmethod
    def get_cache(cls, name: str) -> CacheManager:
        """
        获取指定名称的缓存管理器
        
        参数:
            name: 缓存名称
            
        返回:
            缓存管理器实例
        """
        return CacheManager.get_instance(name)
    
    @classmethod
    def update_cache_config(cls, cache_name: str, config: Dict[str, Any]) -> None:
        """
        更新指定缓存的配置
        
        参数:
            cache_name: 缓存名称
            config: 新的配置
        """
        cls._logger.info(f"更新缓存配置: {cache_name}")
        cls._initialize_single_cache(cache_name, config)
    
    @classmethod
    def is_initialized(cls) -> bool:
        """
        检查缓存系统是否已初始化
        
        返回:
            是否已初始化
        """
        return cls._initialized
    
    @classmethod
    def get_summary(cls) -> Dict[str, Any]:
        """
        获取缓存系统摘要信息
        
        返回:
            包含系统摘要的字典
        """
        all_stats = cls.get_all_stats()
        
        total_caches = len(all_stats)
        total_items = sum(
            stats.get("current_size", 0) 
            for stats in all_stats.values()
        )
        total_hits = sum(
            stats.get("hit_count", 0) 
            for stats in all_stats.values()
        )
        total_misses = sum(
            stats.get("miss_count", 0) 
            for stats in all_stats.values()
        )
        total_requests = total_hits + total_misses
        overall_hit_rate = (
            round(total_hits / total_requests * 100, 2) 
            if total_requests > 0 
            else 0
        )
        
        return {
            "initialized": cls._initialized,
            "total_caches": total_caches,
            "total_cached_items": total_items,
            "total_requests": total_requests,
            "total_hits": total_hits,
            "total_misses": total_misses,
            "overall_hit_rate": overall_hit_rate,
            "caches": list(all_stats.keys())
        }
