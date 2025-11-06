# Text2SQL 缓存优化指南

## 概述

本项目已实现了一个通用、高效且易于扩展的缓存系统，用于优化Text2SQL工具的性能。缓存系统基于以下设计原则：

- **简单高效**：使用内存缓存，基于LRU（最近最少使用）策略
- **易于扩展**：模块化设计，支持其他工具快速集成
- **高可维护性**：清晰的抽象层和统一的接口
- **可监控**：提供详细的缓存统计和管理功能

## 架构设计

### 核心模块

```
service/cache/
├── __init__.py          # 模块导出和初始化
├── base.py              # 缓存抽象基类和管理器
├── memory.py            # 内存缓存实现（LRU、TTL）
├── decorators.py        # 缓存装饰器
├── config.py            # 缓存配置管理
└── utils.py             # 工具函数（查询规范化、键生成等）
```

### 缓存层次

```
┌─────────────────────────────────────────┐
│         应用层（Text2SQL Tool）          │
├─────────────────────────────────────────┤
│        缓存装饰器 / 缓存管理器           │
├─────────────────────────────────────────┤
│      LRU Cache / TTL Cache              │
│      (内存缓存实现)                      │
└─────────────────────────────────────────┘
```

## 已实现的缓存功能

### 1. Schema检索缓存

**位置**: `service/knowledge_service.py`

**功能**: 自动缓存知识库检索结果

**特性**:
- 使用装饰器`@cacheable`实现
- 缓存键基于`dataset_id`、规范化后的`query`、`top_k`和`retrieval_model`
- 默认过期时间：1小时
- 只缓存非空结果

**代码示例**:
```python
@cacheable(
    name="schema_cache",
    key_prefix="schema",
    ttl=3600,
    key_generator=lambda self, dataset_id, query, top_k, retrieval_model: 
        create_cache_key_from_dict(
            "schema",
            {"dataset_id": dataset_id, "query": normalize_query(query), ...}
        ),
    condition=lambda result: result and result.strip()
)
def retrieve_schema_from_dataset(self, dataset_id, query, top_k, retrieval_model):
    # 方法实现...
```

### 2. SQL生成结果缓存

**位置**: `tools/text2sql.py`

**功能**: 缓存LLM生成的SQL查询结果

**特性**:
- 手动控制缓存逻辑，在生成SQL前检查缓存
- 缓存键基于`dialect`、规范化后的`query`、`dataset_id`和部分`custom_prompt`
- 默认过期时间：2小时
- 如果用户重置记忆则不使用缓存

**工作流程**:
```
用户查询 → 检查SQL缓存 → 命中？
    ↓ 是                    ↓ 否
返回缓存SQL          调用LLM生成SQL
    ↓                       ↓
保存对话记录          缓存新生成的SQL
                            ↓
                       返回SQL结果
```

### 3. 查询规范化

**功能**: 提高缓存命中率

**实现**: `service/cache/utils.py` 中的 `normalize_query()`

**处理步骤**:
1. 转换为小写
2. 移除多余空格
3. 移除停用词（如"请"、"帮我"、"查询"等）

**示例**:
```python
normalize_query("  请 帮我  查询 用户信息  ")
# 输出: "用户信息"
```

## 缓存配置

### 默认配置

```python
{
    "schema_cache": {
        "type": "lru",
        "max_size": 100,  # 最多缓存100项
        "ttl": 3600       # 1小时过期
    },
    "sql_cache": {
        "type": "lru",
        "max_size": 50,   # 最多缓存50项
        "ttl": 7200       # 2小时过期
    },
    "prompt_cache": {
        "type": "lru",
        "max_size": 20,   # 最多缓存20项
        "ttl": 86400      # 24小时过期
    }
}
```

### 修改配置

可以通过`CacheConfig`类修改配置：

```python
from service.cache import CacheConfig

# 更新特定缓存配置
CacheConfig.update_cache_config("schema_cache", {
    "type": "lru",
    "max_size": 200,  # 增加缓存大小
    "ttl": 7200       # 增加过期时间到2小时
})
```

## 使用方法

### 方法1：使用装饰器（推荐）

适用于函数/方法级别的缓存：

```python
from service.cache import cacheable

@cacheable(
    name="my_cache",       # 缓存管理器名称
    key_prefix="prefix",   # 缓存键前缀
    ttl=3600,              # 过期时间（秒）
    condition=lambda result: result is not None  # 缓存条件
)
def my_expensive_function(param1, param2):
    # 耗时操作
    return result
```

### 方法2：手动使用缓存管理器

适用于需要精细控制的场景：

```python
from service.cache import CacheManager, create_cache_key_from_dict

# 获取缓存管理器
cache = CacheManager.get_instance("my_cache")

# 生成缓存键
cache_key = create_cache_key_from_dict("prefix", {
    "param1": value1,
    "param2": value2
})

# 检查缓存
cached_result = cache.get(cache_key)
if cached_result:
    return cached_result

# 执行操作
result = expensive_operation()

# 缓存结果
cache.set(cache_key, result, ttl=3600)
```

## 缓存统计与监控

### 获取缓存统计

```python
from service.cache import CacheConfig

# 获取所有缓存的摘要信息
summary = CacheConfig.get_summary()
print(summary)
# 输出示例:
# {
#     "initialized": True,
#     "total_caches": 3,
#     "total_cached_items": 45,
#     "total_requests": 1000,
#     "total_hits": 750,
#     "total_misses": 250,
#     "overall_hit_rate": 75.0,
#     "caches": ["schema_cache", "sql_cache", "prompt_cache"]
# }

# 获取特定缓存的详细统计
stats = CacheManager.get_instance("schema_cache").get_stats()
print(stats)
# 输出示例:
# {
#     "name": "schema_cache",
#     "hit_count": 450,
#     "miss_count": 150,
#     "total_requests": 600,
#     "hit_rate": 75.0,
#     "backend_type": "lru_memory",
#     "max_size": 100,
#     "current_size": 85,
#     "valid_items": 83,
#     "expired_items": 2,
#     "usage_ratio": 85.0,
#     "memory_estimate_bytes": 524288
# }
```

### 缓存管理操作

```python
from service.cache import CacheConfig, CacheManager

# 清空所有缓存
CacheConfig.clear_all_caches()

# 清空特定缓存
CacheManager.get_instance("schema_cache").clear()

# 重置所有统计信息
CacheConfig.reset_all_stats()

# 删除特定缓存项
cache = CacheManager.get_instance("schema_cache")
cache.delete("specific_cache_key")
```

## 性能优化效果

### 预期收益

1. **Schema检索**:
   - 无缓存：每次查询需要200-500ms API调用
   - 有缓存：缓存命中时 < 1ms

2. **SQL生成**:
   - 无缓存：每次需要调用LLM，耗时1-3秒
   - 有缓存：缓存命中时 < 1ms

3. **整体性能**:
   - 在相似查询场景下，响应时间可减少70-90%
   - API调用次数减少60-80%
   - LLM调用成本降低60-80%

### 缓存命中率优化

提高缓存命中率的技巧：

1. **查询规范化**: 已自动实现，将相似查询映射到相同的缓存键
2. **合理的TTL设置**: Schema信息变化较少，可以设置较长的TTL
3. **缓存预热**: 对常见查询提前执行一次以填充缓存
4. **监控和调整**: 定期查看缓存统计，根据实际情况调整配置

## 为其他工具添加缓存

### 示例：为新工具添加缓存支持

```python
from service.cache import cacheable, CacheManager

class MyNewTool:
    def __init__(self):
        # 获取专用缓存管理器
        self._my_cache = CacheManager.get_instance("my_tool_cache")
    
    @cacheable(
        name="my_tool_cache",
        key_prefix="my_tool",
        ttl=1800  # 30分钟
    )
    def my_expensive_method(self, param1, param2):
        # 执行耗时操作
        result = perform_operation(param1, param2)
        return result
```

### 步骤

1. **定义缓存配置**（可选，使用默认配置或在`CacheConfig`中添加）
2. **选择缓存方式**：装饰器或手动缓存管理
3. **实现缓存逻辑**
4. **测试和监控**

## 最佳实践

### DO ✅

1. **对耗时操作使用缓存**: API调用、LLM调用、复杂计算
2. **使用查询规范化**: 提高缓存命中率
3. **设置合理的TTL**: 根据数据变化频率设置过期时间
4. **监控缓存性能**: 定期检查命中率和内存使用
5. **只缓存成功结果**: 使用`condition`参数过滤无效结果

### DON'T ❌

1. **不要缓存频繁变化的数据**: 实时数据不适合长时间缓存
2. **不要过度缓存**: 避免缓存不常用的数据浪费内存
3. **不要忽略缓存失效**: 数据更新时及时清理相关缓存
4. **不要缓存敏感信息**: 避免在缓存中存储密码、密钥等
5. **不要设置过长的TTL**: 可能导致数据不一致

## 故障排查

### 问题1：缓存未生效

**可能原因**:
- 缓存未初始化
- 缓存键生成不一致
- 缓存已过期

**解决方案**:
```python
# 检查缓存是否初始化
from service.cache import CacheConfig
print(CacheConfig.is_initialized())

# 查看缓存统计
stats = CacheConfig.get_all_stats()
print(stats)
```

### 问题2：内存占用过高

**可能原因**:
- 缓存大小配置过大
- 缓存项包含大量数据
- TTL过长导致积累

**解决方案**:
```python
# 减小缓存大小
CacheConfig.update_cache_config("schema_cache", {
    "type": "lru",
    "max_size": 50  # 减少到50
})

# 清理过期项
cache = CacheManager.get_instance("schema_cache")
if hasattr(cache._backend, 'cleanup_expired'):
    cache._backend.cleanup_expired()
```

### 问题3：缓存命中率低

**可能原因**:
- 查询变化大
- TTL设置过短
- 缓存键生成不合理

**解决方案**:
- 使用查询规范化
- 增加TTL时间
- 优化缓存键生成逻辑

## 扩展方向

### 未来可能的扩展

1. **持久化缓存**: 支持Redis等外部缓存
2. **分布式缓存**: 多实例间共享缓存
3. **智能缓存**: 基于ML预测缓存项重要性
4. **缓存预热**: 自动识别热点查询并预加载

### 添加新的缓存后端

```python
from service.cache.base import CacheBackend

class RedisCache(CacheBackend):
    def __init__(self, redis_client, max_size=100):
        self.redis = redis_client
        self.max_size = max_size
    
    def get(self, key):
        return self.redis.get(key)
    
    def set(self, key, value, ttl=None):
        self.redis.set(key, value, ex=ttl)
    
    # 实现其他抽象方法...
```

## 总结

本缓存系统提供了一个简单、高效且易于扩展的解决方案，显著提升了Text2SQL工具的性能。通过合理使用缓存，可以：

- **减少API调用次数**，降低成本
- **加快响应速度**，提升用户体验
- **降低系统负载**，提高吞吐量

遵循最佳实践，定期监控和优化，可
