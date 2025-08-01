# SchemaRAG 数据库架构RAG插件

[![Version](https://img.shields.io/badge/version-0.0.4-blue.svg)](https://github.com/weijunjiang123/schemarag)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://www.python.org/)

**作者:** joto  
**版本:** 0.0.4  
**类型:** 工具
**仓库:** https://github.com/JOTO-AI/SchemaRAG-dify-plugin

---

## 概述

SchemaRAG 是一个专为 Dify 平台设计的数据库架构RAG插件，能够自动分析数据库结构、构建知识库并实现自然语言转SQL查询。该插件提供了完整的数据库schema分析和智能查询解决方案，开箱即用。

---

## ✨ 核心功能

- **多数据库支持**: MySQL & PostgreSQL，自动适配语法差异
- **架构自动分析**: 一键生成数据字典，结构可视化
- **知识库上传**: 自动上传到 Dify，支持增量更新
- **自然语言转SQL**: 开箱即用，支持复杂查询
- **安全机制**: 仅限SELECT，支持字段白名单，最低权限原则
- **灵活支持**: 兼容主流大模型

---

## 📋 配置参数

| 参数名            | 类型     | 必填 | 说明                         | 示例                      |
|------------------|----------|------|------------------------------|---------------------------|
| Dataset API Key  | secret   | 是   | Dify知识库API密钥             | dataset-xxx               |
| Database Type    | select   | 是   | 数据库类型 MySQL/PostgreSQL   | MySQL                     |
| Database Host    | string   | 是   | 数据库主机/IP                 | 127.0.0.1                 |
| Database Port    | number   | 是   | 数据库端口                    | 3306/5432                 |
| Database User    | string   | 是   | 数据库用户名                  | root                      |
| Database Password| secret   | 是   | 数据库密码                    | ******                    |
| Database Name    | string   | 是   | 数据库名称                    | mydb                      |
| Dify Base URL    | string   | 否   | Dify API基础URL               | `https://api.dify.ai/v1`  |

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

通过配置连接数据库，自动构建数据库 schema 知识库，在工作流中连接知识库即可实现 text2sql 的功能，开箱即用。

### 2. sql_executer 工具

提供安全的接口在 Dify 工作流中实现数据库查询的功能，可以指定 markdown 和 json 两种输出格式。

### 3. text2data 工具

封装上述两种工具，开箱即用，增加 LLM 总结功能，将查询的数据总结成报告输出。


---

## ❓ 常见问题

**Q: 支持哪些数据库？**  
A: 当前支持 MySQL 和 PostgreSQL。

**Q: 数据是否安全？**  
A: 插件仅读取数据库结构信息，构建 Dify 知识库，敏感信息不会上传。

**Q: 如何配置数据库？**  
A: 在 Dify 插件页面中配置数据库和知识库相关信息，配置完成后会自动在 Dify 中构建 schema 知识库。

**Q: 如何使用 text2sql 工具？**  
A: 在配置好数据库并生成 schema 知识库后，需要在生成的知识库 URL 中获取 dataset_id 并填入工具中，指定索引的知识库，并且配置好其他信息即可使用。

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