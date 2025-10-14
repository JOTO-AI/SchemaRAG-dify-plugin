# Text2SQL 上下文记忆功能使用指南

## 概述

Text2SQL工具现在支持多轮对话记忆功能，可以记住之前的对话历史，实现更智能的上下文理解和SQL生成。

## 功能特性

### 1. 多轮对话记忆
- 自动记录每次对话的问题和生成的SQL
- 支持可配置的记忆窗口大小（1-10轮）
- 基于用户ID实现多用户隔离

### 2. 智能上下文理解
- 当用户问题引用之前的查询时，系统会自动加载历史对话
- LLM可以基于历史上下文生成更准确的SQL

### 3. 灵活的记忆控制
- 可以随时启用/禁用记忆功能
- 支持重置记忆，清除所有历史对话
- 自动过期清理，防止内存泄漏

## 参数说明

### memory_enabled (启用记忆功能)
- **类型**: boolean
- **必填**: 否
- **默认值**: false
- **说明**: 是否启用上下文记忆功能。设置为true时，系统会记住历史对话。

### memory_window_size (记忆窗口大小)
- **类型**: number
- **必填**: 否
- **默认值**: 3
- **范围**: 1-10
- **说明**: 记住最近几轮对话的数量。数值越大，记忆的历史越多，但也会占用更多的token。

### reset_memory (重置记忆)
- **类型**: boolean
- **必填**: 否
- **默认值**: false
- **说明**: 是否清除当前用户的所有对话历史。设置为true时会清空记忆，适合开始新的对话主题。

## 使用场景

### 场景1：连续查询细化
```
用户: 查询所有用户
系统: SELECT * FROM users

用户: 只要活跃用户
系统: SELECT * FROM users WHERE status = 'active'

用户: 按注册日期排序
系统: SELECT * FROM users WHERE status = 'active' ORDER BY created_at DESC
```

### 场景2：数据分析深入
```
用户: 查询上个月的销售额
系统: SELECT SUM(amount) FROM orders WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 MONTH)

用户: 按产品类别分组
系统: SELECT category, SUM(amount) FROM orders WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 MONTH) GROUP BY category

用户: 显示前10名
系统: SELECT category, SUM(amount) as total FROM orders WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 MONTH) GROUP BY category ORDER BY total DESC LIMIT 10
```

### 场景3：表关联查询
```
用户: 查询用户信息
系统: SELECT * FROM users

用户: 关联他们的订单
系统: SELECT u.*, o.* FROM users u LEFT JOIN orders o ON u.id = o.user_id

用户: 只要有订单的用户
系统: SELECT u.*, o.* FROM users u INNER JOIN orders o ON u.id = o.user_id
```

## 最佳实践

### 1. 何时启用记忆功能

**适合启用的场景**:
- 需要多次细化同一个查询
- 进行数据分析时的连续探索
- 构建复杂查询的过程
- 用户可能引用之前的结果

**不适合启用的场景**:
- 独立的、不相关的查询
- 一次性的简单查询
- 需要完全独立上下文的查询

### 2. 选择合适的窗口大小

- **窗口大小 1-2**: 适合简单的连续细化，节省token
- **窗口大小 3-5**: 平衡性能和上下文，适合大多数场景（推荐）
- **窗口大小 6-10**: 适合复杂的多步骤分析，但会消耗更多token

### 3. 及时重置记忆

在以下情况应该重置记忆:
- 开始新的查询主题时
- 切换到不同的数据库或表时
- 之前的上下文已经不再相关时
- 发现生成的SQL受到错误历史影响时

## 技术架构

### 模块结构

```
service/context/
├── __init__.py              # 模块导出
├── models.py                # 数据模型（Conversation, UserContext）
├── storage.py               # 存储层（MemoryContextStorage）
└── context_manager.py       # 核心管理器（ContextManager）

prompt/components/
├── __init__.py
└── context_formatter.py     # 上下文格式化组件
```

### 核心组件

#### 1. ContextManager
负责高级别的上下文操作:
- 获取和保存对话历史
- 管理用户上下文
- 自动清理过期数据

#### 2. ContextStorage
抽象存储层，支持不同的存储后端:
- 当前实现: MemoryContextStorage（内存存储）
- 可扩展: RedisContextStorage, DatabaseContextStorage等

#### 3. Conversation & UserContext
数据模型:
- Conversation: 单轮对话（问题+SQL+元数据）
- UserContext: 用户上下文（用户ID+对话列表+时间戳）

#### 4. ContextFormatter
格式化组件:
- 将对话历史格式化为提示词片段
- 智能判断是否需要包含上下文

### 数据流程

```
1. 用户提问
   ↓
2. 检查是否启用记忆 & 不是重置操作
   ↓
3. 从ContextManager获取历史对话
   ↓
4. ContextFormatter格式化历史为提示词
   ↓
5. 构建完整的system prompt
   ↓
6. 调用LLM生成SQL
   ↓
7. 如果启用记忆，保存本轮对话到ContextManager
```

## 性能考虑

### 内存管理
- 使用类级别的共享存储实例，避免重复创建
- 自动清理24小时未访问的上下文
- 每小时执行一次自动清理

### Token优化
- 历史对话只包含问题和SQL，不包含其他元数据
- 可配置的窗口大小控制历史长度
- 智能判断是否需要包含上下文（基于关键词检测）

### 线程安全
- 使用可重入锁（RLock）保护共享数据
- 支持并发访问和修改
- 无竞态条件

## 示例代码

### 基本使用
```python
from service.context import ContextManager

# 创建上下文管理器
cm = ContextManager()

# 添加对话
cm.add_conversation(
    query="查询所有用户",
    sql="SELECT * FROM users",
    user_id="user_123",
    metadata={"dialect": "mysql"}
)

# 获取历史
history = cm.get_conversation_history(
    user_id="user_123",
    window_size=3
)

# 重置记忆
cm.reset_memory(user_id="user_123")
```

### 在Tool中使用
```python
# 获取历史（如果启用）
conversation_history = []
if memory_enabled and not reset_memory:
    conversation_history = self._context_manager.get_conversation_history(
        user_id=user_id,
        window_size=memory_window_size
    )

# 构建带上下文的prompt
system_prompt = text2sql_prompt._build_system_prompt(
    dialect, schema_info, content, 
    custom_prompt, example_info, conversation_history
)

# 保存本轮对话
if memory_enabled and generated_sql:
    self._context_manager.add_conversation(
        query=content,
        sql=generated_sql,
        user_id=user_id,
        metadata={"dialect": dialect}
    )
```

## 故障排除

### 问题1: 生成的SQL不正确且似乎受到历史影响
**解决方案**: 
- 设置 `reset_memory=true` 清除历史
- 检查 `memory_window_size` 是否过大
- 确认历史对话的SQL是否正确

### 问题2: 系统没有使用历史上下文
**解决方案**:
- 确认 `memory_enabled=true`
- 确认没有设置 `reset_memory=true`
- 检查用户ID是否一致
- 查看日志确认是否加载了历史

### 问题3: 内存占用过高
**解决方案**:
- 减小 `memory_window_size`
- 增加重置记忆的频率
- 检查是否有大量不同的用户ID

## 测试

运行测试验证功能:

```bash
python test/test_context_manager.py
```

测试包括:
- 基本上下文操作
- 多用户隔离
- 记忆窗口大小
- 数据模型序列化

## 未来扩展

### 计划中的功能
1. **持久化存储**: 支持Redis/Database作为存储后端
2. **上下文压缩**: 自动总结长历史为简短描述
3. **智能上下文选择**: 基于语义相似度选择相关历史
4. **跨会话记忆**: 支持跨多个会话的长期记忆
5. **上下文分析**: 提供上下文使用统计和分析

### 扩展存储后端示例

```python
# Redis存储后端示例
class RedisContextStorage(ContextStorage):
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def get_context(self, context_key: str) -> Optional[UserContext]:
        data = self.redis.get(context_key)
        if data:
            return UserContext.from_dict(json.loads(data))
        return None
    
    def save_context(self, user_context: UserContext) -> bool:
        self.redis.set(
            user_context.context_key,
            json.dumps(user_context.to_dict()),
            ex=86400  # 24小时过期
        )
        return True
```

## 总结

上下文记忆功能为Text2SQL工具带来了智能的多轮对话能力，使其能够更好地理解用户意图，生成更准确的SQL查询。通过合理配置和使用，可以大大提升用户体验和查询效率。
