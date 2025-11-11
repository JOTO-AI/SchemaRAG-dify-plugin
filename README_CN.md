# SchemaRAG 数据库架构RAG插件

[![Version](https://img.shields.io/badge/version-0.1.2-blue.svg)](https://github.com/weijunjiang123/schemarag)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://www.python.org/)

**作者:** joto  
**版本:** 0.1.2  
**类型:** 工具
**仓库:** <https://github.com/JOTO-AI/SchemaRAG-dify-plugin>

---

<img src="./_assets/logo.jpg" height="100" alt="logo" style="border-radius:10px;">

## 概述

SchemaRAG 是一个专为 Dify 平台设计的数据库架构RAG插件，能够自动分析数据库结构、构建知识库并实现自然语言转SQL查询。该插件提供了完整的数据库schema分析和智能查询解决方案，开箱即用。

示例工作流[下载](https://github.com/JOTO-AI/SchemaRAG-dify-plugin/blob/main/demo/text2sql-workflow.yml)

---

## ✨ 核心功能

- **多数据库支持**: MySQL, PostgreSQL, MSSQL, Oracle, 达梦自动适配语法差异
- **schema自动分析**: 一键生成数据字典，结构可视化
- **知识库上传**: 自动上传到 Dify，支持增量更新
- **自然语言转SQL**: 开箱即用，支持复杂查询
- **AI 数据分析**：分析查询数据，支持自定义规则
- **数据可视化**：提供可视化工具，llm推荐图表和字段
- **安全机制**: 仅限SELECT，支持字段白名单，最低权限原则
- **灵活支持**: 兼容主流大模型

---

## 📋 配置参数

| 参数名            | 类型     | 必填 | 说明                         | 示例                      |
|------------------|----------|------|------------------------------|---------------------------|
| Dataset API Key  | secret   | 是   | Dify知识库API密钥             | dataset-xxx               |
| Database Type    | select   | 是   | 数据库类型 MySQL/PostgreSQL... | MySQL                     |
| Database Host    | string   | 是   | 数据库主机/IP                 | 127.0.0.1                 |
| Database Port    | number   | 是   | 数据库端口                    | 3306/5432                 |
| Database User    | string   | 是   | 数据库用户名                  | root                      |
| Database Password| secret   | 是   | 数据库密码                    | ******                    |
| Database Name    | string   | 是   | 数据库名称                    | mydb                      |
| Dify Base URL    | string   | 否   | Dify API基础URL               | `https://api.dify.ai/v1`  |

## 支持的数据库类型

| 数据库类型 | 默认端口 | 驱动程序 | 连接字符串格式 |
|------------|----------|----------|----------------|
| MySQL | 3306 | pymysql | `mysql+pymysql://user:password@host:port/database` |
| PostgreSQL | 5432 | psycopg2-binary | `postgresql://user:password@host:port/database` |
| Microsoft SQL Server | 1433 | pymssql | `mssql+pymssql://user:password@host:port/database` |
| Oracle | 1521 | oracledb | `oracle+oracledb://user:password@host:port/database` |
| 达梦数据库 | 5236 | dm+pymysql | `dm+pymysql://user:password@host:port/database` |

---

## 🚀 快速开始

### 方式一：命令行运行

```bash
uv run main.py 
```

### 方式二：Dify 插件集成

1. 在 Dify 平台插件配置界面填写上述参数
![插件配置](./_assets/image-1.png)

2. 在配置好，准确无误后点击保存，会自动在dify中构建配置的数据库schema知识库

3. 在工作流中添加工具，并配置刚刚创建的知识库id（知识库id在知识库页面的URL处）
![工作流节点配置](./_assets/image-4.png)

4. 提供sql执行工具，传入生成的sql可直接执行，支持md，json输出
![工作流节点配置](./_assets/image-5.png)

### 方式三：代码调用

```python
from provider.build_schema_rag import BuildSchemaRAG

builder = BuildSchemaRAG(
    dataset_api_key="your-key",
    db_type="MySQL",
    db_host="localhost",
    db_port=3306,
    db_user="root",
    db_password="password",
    db_name="your_db"
)
result = builder.toschema()
print(result)
```

---

## 🛠️ 工具组件

### 1. text2sql 工具

**自然语言转SQL查询工具** - 使用数据库架构知识库将自然语言问题转换为SQL查询

#### 核心功能

- **智能查询转换**: 将自然语言问题自动转换为准确的SQL查询语句
- **多数据库支持**: 支持MySQL和PostgreSQL两种SQL方言
- **知识库检索**: 基于数据库架构知识库进行智能检索和匹配
- **开箱即用**: 配置好知识库即可直接使用，无需额外设置
- **自定义prompt规则**: 添加自定以提示词，配置自定义规则

#### 参数说明

| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| dataset_id | string | 是 | 包含数据库架构的Dify知识库ID |
| llm | model-selector | 是 | 用于生成SQL的大语言模型 |
| content | string | 是 | 要转换为SQL的自然语言问题 |
| dialect | select | 是 | SQL方言（MySQL/PostgreSQL）|
| top_k | number | 否 | 从知识库检索的结果数量（默认5）|

### 2. sql_executer 工具

**SQL查询执行工具** - 安全执行SQL查询并返回格式化结果

#### 核心功能

- **安全执行**: 仅支持SELECT查询，确保数据安全
- **最大输出控制**： 提供接口控制最大查询行数，方式查询数据过多。
- **多格式输出**: 支持JSON和Markdown两种输出格式
- **直接连接**: 直接连接数据库执行查询，实时获取结果
- **错误处理**: 完善的错误处理机制，提供详细的错误信息

#### 参数说明

| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| sql | string | 是 | 要执行的SQL查询语句 |
| output_format | select | 是 | 输出格式（JSON/Markdown）|
| max_line | int | 否 | 查询到的最大行数（默认1000行）|

### 3. sql_executer_cust 工具

**自定义SQL查询执行工具** - 自定义数据库并安全执行SQL查询并返回格式化结果

#### 核心功能

- **自定义数据库连接**：支持多种数据库无需配置插件即可用
- **安全执行**: 仅支持SELECT查询，确保数据安全
- **最大输出控制**： 提供接口控制最大查询行数，方式查询数据过多。
- **多格式输出**: 支持JSON和Markdown两种输出格式
- **直接连接**: 直接连接数据库执行查询，实时获取结果
- **错误处理**: 完善的错误处理机制，提供详细的错误信息

#### 参数说明

| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| database_url | string | 是 | 数据库连接url |
| sql | string | 是 | 要执行的SQL查询语句 |
| output_format | select | 是 | 输出格式（JSON/Markdown）|
| max_line | int | 否 | 查询到的最大行数（默认1000行）|

数据库连接url示例：
- mysql：mysql://user:password@host:port/dbname
- postgresql: postgresql://user:password@host:port/dbname
- dameng: dameng://user:password@host:port/dbname
- mssql: mssql://user:password@host:port/dbname
- oracle: oracle://user:password@host:port/dbname

### 4. text2data 工具（删除）

**注意：**
此插件在v0.0.7移除，原因是在dify版本1.7.1使用此插件会导致工作流前端崩溃，后续dify会修复[dify issue](https://github.com/langgenius/dify/issues/23154)。请注意版本慎用此工具。

封装上述两种工具，开箱即用，增加 LLM 总结功能，将查询的数据总结成报告输出。

### 5. data_summary 工具

**数据总结分析工具** - 使用大语言模型对数据内容进行智能分析和总结

#### 分析能力

- **自定义规则**: 支持用户定义分析规则和指导原则
- **数据格式智能识别**: 自动识别JSON等数据格式并优化处理
- **性能优化**: 缓存常用配置，减少响应时间

#### 配置选项

| 参数名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| data_content | string | 是 | 需要分析的数据内容 |
| llm | model-selector | 是 | 用于分析的大语言模型 |
| query | string | 是 | 分析查询或关注领域 |
| custom_rules | string | 否 | 自定义分析规则 |
| user_prompt | string | 否 | 自定义prompt |

### 6. llm_chart_generator 工具

**LLM 智能绘图模块** - 基于大语言模型推荐图标类型和字段，使用[antv](https://github.com/antvis/)渲染图表功能，提供高可维护的端到端图表解决方案

#### 功能特性

- **智能分析**: 自动分析用户问题和数据，智能选择最合适的图表类型
- **多图表支持**: 支持折线图、饼图、直方图等主流图表
- **高可维护性**: 模块化设计，接口清晰，易于扩展和维护
- **统一规范**: 图表配置采用标准化 JSON 格式，便于集成和解析
- **降级方案**: 图表生成失败时自动降级为表格等展示方式
- **配置验证**: 完善的配置校验和错误处理机制，保障稳定性

#### 配置选项

| 参数名         | 类型           | 必填 | 描述                                                         |
|----------------|----------------|------|--------------------------------------------------------------|
| user_question  | string         | 是   | 用户问题，描述需要生成的图表类型和需求（如销售趋势、市场份额）|
| data           | string         | 是   | 用于可视化的数据，支持 JSON、CSV 或结构化数据                |
| llm            | model-selector | 是   | 用于分析和生成图表的大语言模型                               |
| sql_query        | string         | 是   | 查询的sql语句，用于推荐图表和字段                           |


---

## ❓ 常见问题

**Q: 支持哪些数据库？**  
A: 当前支持 MySQL, PostgreSQL, MSSQL, Oracle, 达梦 。

**Q: 数据是否安全？**  
A: 插件仅读取数据库结构信息，构建 Dify 知识库，敏感信息不会上传。

**Q: 如何配置数据库？**  
A: 在 Dify 插件页面中配置数据库和知识库相关信息，配置完成后会自动在 Dify 中构建 schema 知识库。

**Q: 如何使用 text2sql 工具？**  
A: 在配置好数据库并生成 schema 知识库后，需要在生成的知识库 URL 中获取 dataset_id 并填入工具中，指定索引的知识库，并且配置好其他信息即可使用。

**Q: data_summary 工具支持哪些数据格式？**  
A: 支持文本、JSON 等多种数据格式，工具会自动识别并优化处理。支持最大 50,000 字符的数据内容。

**Q: 自定义规则如何使用？**  
A: 可以在 custom_rules 参数中指定特定的分析要求、关注点或约束条件，最大支持 2,000 字符。

---

## 📸 示例截图

![Schema 构建界面](./_assets/image-0.png)

![查询结果展示](./_assets/image-2.png)

![数据总结报告](./_assets/image-3.png)

---

## 📞 联系方式

- **开发者**: [Dylan Jiang](https://github.com/weijunjiang123)
- **邮箱**: <weijun.jiang@jototech.cn>

---

## 📄 许可证

Apache-2.0 license
