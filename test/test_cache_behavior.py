#!/usr/bin/env python3
"""
测试缓存后端、缓存管理器和缓存装饰器
"""

import pytest

from service.cache.base import CacheManager
from service.cache.decorators import cacheable, invalidate_cache
from service.cache.memory import LRUCache, TTLCache
from service.cache.utils import (
    batch_normalize_queries,
    create_cache_key_from_dict,
    generate_cache_key,
    is_cache_key_valid,
    normalize_query,
    sanitize_cache_key,
)


def test_lru_cache_eviction_expiry_and_cleanup():
    """LRU 后端应支持容量淘汰、TTL 过期和过期清理。"""
    cache = LRUCache(max_size=2)
    cache.set("a", 1)
    cache.set("b", 2)
    assert cache.get("a") == 1

    cache.set("c", 3)
    assert cache.get("b") is None
    assert cache.get("a") == 1
    assert cache.get("c") == 3

    cache.set("expired", "value", ttl=0)
    assert cache.get("expired") is None

    cache.set("expired-1", "value", ttl=0)
    cache.set("expired-2", "value", ttl=0)
    assert cache.cleanup_expired() == 2


def test_lru_cache_rejects_invalid_max_size():
    """LRU 后端容量必须为正数。"""
    with pytest.raises(ValueError, match="max_size必须大于0"):
        LRUCache(max_size=0)


def test_ttl_cache_expiry_eviction_and_stats():
    """TTL 后端应按过期时间读取，并在满容量时淘汰旧项。"""
    cache = TTLCache(max_size=2, default_ttl=3600)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)

    assert cache.get("a") is None
    assert cache.get("b") == 2
    assert cache.get("c") == 3

    cache.set("expired", "value", ttl=0)
    assert cache.get("expired") is None

    stats = cache.get_stats()
    assert stats["backend_type"] == "ttl_memory"
    assert stats["max_size"] == 2


def test_cache_manager_tracks_hits_misses_and_can_reset_stats():
    """CacheManager 应统计命中/未命中，并支持重置统计。"""
    manager = CacheManager("unit-cache-manager")
    manager.set_backend(LRUCache(max_size=2))

    manager.set("key", "value")
    assert manager.get("key") == "value"
    assert manager.get("missing") is None

    stats = manager.get_stats()
    assert stats["hit_count"] == 1
    assert stats["miss_count"] == 1
    assert stats["hit_rate"] == 50.0

    manager.reset_stats()
    assert manager.get_stats()["total_requests"] == 0


def test_cacheable_decorator_caches_results_and_supports_cache_clear():
    """cacheable 装饰器应缓存结果，并提供 cache_clear 控制。"""
    calls = {"count": 0}

    @cacheable(name="unit-cacheable", key_prefix="double")
    def double(value):
        calls["count"] += 1
        return value * 2

    double.cache_clear()
    assert double(3) == 6
    assert double(3) == 6
    assert calls["count"] == 1

    double.cache_clear()
    assert double(3) == 6
    assert calls["count"] == 2


def test_cacheable_condition_and_invalidate_cache():
    """条件缓存只缓存满足条件的结果，失效装饰器可清空缓存。"""
    calls = {"count": 0}

    @cacheable(
        name="unit-conditional-cache",
        key_prefix="maybe",
        condition=lambda result: result is not None,
    )
    def maybe(value):
        calls["count"] += 1
        return value

    @invalidate_cache("unit-conditional-cache")
    def clear_cache_side_effect():
        return "ok"

    maybe.cache_clear()
    assert maybe(None) is None
    assert maybe(None) is None
    assert calls["count"] == 2

    assert maybe("cached") == "cached"
    assert maybe("cached") == "cached"
    assert calls["count"] == 3

    assert clear_cache_side_effect() == "ok"
    assert maybe("cached") == "cached"
    assert calls["count"] == 4


def test_cache_key_utilities_are_stable_and_sanitize_long_keys():
    """缓存键工具应稳定、可规范化并处理超长/非法字符。"""
    assert normalize_query(" 请 帮我 查询 用户 信息 ") == "用户 信息"
    assert batch_normalize_queries(["查询 A", "获取 B"]) == ["a", "b"]
    assert generate_cache_key("prefix", "x", page=1).startswith("prefix:")
    assert create_cache_key_from_dict("schema", {"b": 2, "a": 1}) == (
        create_cache_key_from_dict("schema", {"a": 1, "b": 2})
    )

    sanitized = sanitize_cache_key("bad key/with spaces", max_length=250)
    assert sanitized == "bad_key_with_spaces"

    long_key = "prefix:" + "x" * 400
    compact = sanitize_cache_key(long_key, max_length=90)
    assert len(compact) <= 90
    assert is_cache_key_valid(compact)
    assert not is_cache_key_valid(None)
    assert not is_cache_key_valid([])
