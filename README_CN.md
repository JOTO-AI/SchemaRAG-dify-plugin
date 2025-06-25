# SchemaRAG 数据库架构RAG插件

**作者:** joto  
**版本:** 0.0.1  
**类型:** 工具

---

## 描述

这是一个用于自动分析数据库结构、构建知识库并实现自然语言转SQL的 Dify 插件，包含开箱即用的自然语言转sql的节点工具。

---

## 声明

感谢大家对本项目的关注，您的反馈对插件优化非常重要，欢迎加入社区讨论与合作！

---

## ✨ 核心功能

- **多数据库支持**: MySQL & PostgreSQL，自动适配语法差异
- **架构自动分析**: 一键生成数据字典，结构可视化
- **知识库上传**: 自动上传到 Dify，支持增量更新
- **自然语言转SQL**: 开箱即用，支持复杂查询
- **安全机制**: 仅限SELECT，支持字段白名单，最低权限原则
- **灵活支持**: 兼容主流大模型

---

## 配置参数

| 参数名            | 类型     | 必填 | 说明                         | 示例                   |
|------------------|----------|------|------------------------------|------------------------|
| Dataset API Key  | secret   | 是   | Dify知识库API密钥             | dataset-xxx            |
| Database Type    | select   | 是   | 数据库类型 MySQL/PostgreSQL   | MySQL                  |
| Database Host    | string   | 是   | 数据库主机/IP                 | 127.0.0.1              |
| Database Port    | number   | 是   | 数据库端口                    | 3306/5432              |
| Database User    | string   | 是   | 数据库用户名                  | root                   |
| Database Password| secret   | 是   | 数据库密码                    | ******                 |
| Database Name    | string   | 是   | 数据库名称                    | mydb                   |
| Dify Base URL    | string   | 否   | Dify API基础URL               | <https://api.dify.ai/v1> |

---

## 🚀 快速开始

### 1. 命令行方式

```bash
uv run main.py 
```

### 2. Dify 插件集成

在 Dify 平台插件配置界面，填写上述参数，保存后即可在工作流中拖入使用。

### 3. 代码调用示例

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

## 示例截图

![截图1](./image/image.png)

![截图2](./image/image-1.png)

![截图3](./image/image-2.png)

![截图4](./image/image-3.png)

---

## 常见问题

**Q: 支持哪些数据库？**  
A: 当前支持 MySQL 和 PostgreSQL。

**Q: 数据是否安全？**  
A: 插件仅读取数据库结构信息，构建dify知识库，敏感信息不会上传。

---

## 联系方式

- 开发者：[dylan jiang](https://github.com/weijunjiang123)
- 邮箱：<weijun.jiang@jototech.cn>

---

## 许可证

