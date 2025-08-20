# 动态配置和多知识库支持功能文档

本文档描述了SchemaRAG-dify-plugin中新增的动态配置和多知识库支持功能。

## 新功能概览

### 1. 多知识库支持 (Multiple Knowledge Bases Support)

现在可以同时从多个Dify知识库检索架构信息，提供更全面的数据库架构覆盖。

**使用方法：**
- 在 `dataset_id` 参数中提供逗号分隔的知识库ID
- 例如：`"dataset1,dataset2,dataset3"`
- 系统将从每个知识库中检索相关内容并合并结果

**支持的工具：**
- text2sql
- text2data

**示例：**
```
dataset_id: "db_schema_users,db_schema_orders,db_schema_products"
```

### 2. 自定义助理提示 (Custom Assistant Prompts)

允许用户提供自定义指令来增强SQL生成的系统提示，提高生成结果的质量和针对性。

**使用方法：**
- 在 `custom_prompt` 参数中提供自定义指令
- 自定义提示将被添加到系统提示的"Custom Instructions"部分

**支持的工具：**
- text2sql
- text2data

**示例：**
```
custom_prompt: "Always use explicit column names, avoid SELECT *, and prefer JOIN over subqueries for better performance."
```

### 3. 动态数据库配置 (Dynamic Database Configuration)

支持在工具级别覆盖数据库连接参数，无需修改provider级别的配置。

**使用方法：**
- 提供数据库连接参数作为工具参数
- 如果未提供，将回退到provider配置
- 所有参数都是可选的，支持部分覆盖

**支持的工具：**
- sql_executer
- text2data

**可配置参数：**
- `db_type`: 数据库类型 (mysql, postgresql, mssql, oracle, dameng, doris)
- `db_host`: 数据库主机地址
- `db_port`: 数据库端口号
- `db_user`: 数据库用户名
- `db_password`: 数据库密码
- `db_name`: 数据库名称

**示例：**
```
db_type: "postgresql"
db_host: "prod-db.example.com"
db_port: "5432"
db_user: "analytics_user"
db_password: "secure_password"
db_name: "analytics_db"
```

## 向后兼容性

所有新功能都保持向后兼容：

1. **多知识库支持**：单个知识库ID仍然有效，系统会自动处理
2. **自定义提示**：可选参数，不提供时使用默认系统提示
3. **动态数据库配置**：可选参数，不提供时使用provider配置

## 使用场景

### 多知识库场景
- 不同团队维护不同的架构文档
- 按业务模块分离的数据库架构
- 需要跨多个数据源进行查询

### 自定义提示场景
- 特定的SQL编码标准
- 性能优化要求
- 特定业务逻辑约束

### 动态数据库配置场景
- 多环境部署（开发、测试、生产）
- 临时数据分析任务
- 不同用户权限的数据库访问

## 最佳实践

1. **多知识库使用**：
   - 按逻辑分组组织知识库
   - 确保知识库内容不冗余
   - 定期维护和更新架构文档

2. **自定义提示**：
   - 保持提示简洁明确
   - 避免与系统提示冲突
   - 根据具体业务需求定制

3. **动态数据库配置**：
   - 敏感信息使用安全的参数传递方式
   - 验证连接参数的正确性
   - 考虑配置的复用性