"""
缓存装饰器 - 简化缓存应用的装饰器

该模块提供了便捷的装饰器，用于为函数/方法添加缓存功能，
支持：
- 自动缓存键生成
- 自定义键生成函数
- TTL配置
- 条件缓存
"""

import functools
from typing import Any, Callable, Optional
import logging

from .base import CacheManager
from .utils import generate_cache_key


def cacheable(
    name: str = "default",
    key_prefix: str = "",
    ttl: Optional[int] = None,
    key_generator: Optional[Callable] = None,
    condition: Optional[Callable] = None
):
    """
    函数/方法结果缓存装饰器
    
    参数:
        name: 缓存管理器名称，默认"default"
        key_prefix: 缓存键前缀，默认为空
        ttl: 缓存生存时间（秒），None表示使用缓存管理器的默认TTL
        key_generator: 自定义缓存键生成函数，接收函数的args和kwargs
        condition: 条件函数，返回True时才缓存结果
    
    示例:
        ```python
        @cacheable(name="schema_cache", key_prefix="schema", ttl=3600)
        def fetch_schema(dataset_id: str, query: str):
            # 耗时操作
            return schema_data
        
        # 使用自定义键生成器
        @cacheable(
            name="custom_cache",
            key_generator=lambda *args, **kwargs: f"key:{args[0]}"
        )
        def process_data(id: str):
            return result
        
        # 条件缓存（只缓存成功结果）
        @cacheable(
            name="result_cache",
            condition=lambda result: result is not None
        )
        def compute(x: int):
            return x * 2
        ```
    """
    logger = logging.getLogger(__name__)
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 获取缓存管理器
            cache_manager = CacheManager.get_instance(name)
            
            # 生成缓存键
            if key_generator:
                try:
                    cache_key = key_generator(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"自定义键生成器失败: {e}，使用默认生成器")
                    cache_key = generate_cache_key(
                        key_prefix or func.__name__, 
                        *args, 
                        **kwargs
                    )
            else:
                # 默认键生成逻辑：前缀 + 函数名 + 参数哈希
                cache_key = generate_cache_key(
                    key_prefix or func.__name__, 
                    *args, 
                    **kwargs
                )
            
            # 尝试从缓存获取
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"缓存命中，函数: {func.__name__}, 键: {cache_key}")
                return cached_result
            
            # 缓存未命中，执行原始函数
            logger.debug(f"缓存未命中，执行函数: {func.__name__}")
            result = func(*args, **kwargs)
            
            # 检查是否应该缓存结果
            should_cache = True
            if condition is not None:
                try:
                    should_cache = condition(result)
                except Exception as e:
                    logger.warning(f"条件函数执行失败: {e}，默认缓存结果")
            
            # 缓存结果
            if should_cache:
                cache_manager.set(cache_key, result, ttl)
                logger.debug(f"缓存结果，函数: {func.__name__}, 键: {cache_key}")
            
            return result
        
        # 添加缓存控制方法
        wrapper.cache_clear = lambda: CacheManager.get_instance(name).clear()
        wrapper.cache_info = lambda: CacheManager.get_instance(name).get_stats()
        
        return wrapper
    
    return decorator


def cache_result(
    cache_manager_name: str,
    ttl: Optional[int] = None,
    key_func: Optional[Callable] = None
):
    """
    简化版缓存装饰器，用于快速添加缓存功能
    
    参数:
        cache_manager_name: 缓存管理器名称
        ttl: 过期时间（秒）
        key_func: 键生成函数
    
    示例:
        ```python
        @cache_result("my_cache", ttl=600)
        def expensive_operation(x, y):
            return x + y
        ```
    """
    return cacheable(
        name=cache_manager_name,
        ttl=ttl,
        key_generator=key_func
    )


def invalidate_cache(cache_manager_name: str, key: Optional[Any] = None):
    """
    缓存失效装饰器，在函数执行后清除指定缓存
    
    参数:
        cache_manager_name: 缓存管理器名称
        key: 要清除的缓存键，None表示清空整个缓存
    
    示例:
        ```python
        @invalidate_cache("schema_cache")
        def update_schema(dataset_id: str):
            # 更新操作
            pass
        ```
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # 执行后清除缓存
            cache_manager = CacheManager.get_instance(cache_manager_name)
            if key is None:
                cache_manager.clear()
            else:
                cache_manager.delete(key)
            
            return result
        return wrapper
    return decorator


class CachedProperty:
    """
    缓存属性装饰器，用于类属性的惰性求值和缓存
    
    示例:
        ```python
        class MyClass:
            @CachedProperty
            def expensive_property(self):
                # 耗时计算
                return compute_result()
        
        obj = MyClass()
        result = obj.expensive_property  # 首次计算并缓存
        result = obj.expensive_property  # 直接返回缓存值
        ```
    """
    
    def __init__(self, func: Callable):
        self.func = func
        self.attr_name = f"_cached_{func.__name__}"
        functools.update_wrapper(self, func)
    
    def __get__(self, instance, owner):
        if instance is None:
            return self
        
        # 检查是否已缓存
        if not hasattr(instance, self.attr_name):
            # 计算并缓存结果
            result = self.func(instance)
            setattr(instance, self.attr_name, result)
        
        return getattr(instance, self.attr_name)
    
    def __set__(self, instance, value):
        # 允许手动设置缓存值
        setattr(instance, self.attr_name, value)
    
    def __delete__(self, instance):
        # 允许删除缓存
        if hasattr(instance, self.attr_name):
            delattr(instance, self.attr_name)
