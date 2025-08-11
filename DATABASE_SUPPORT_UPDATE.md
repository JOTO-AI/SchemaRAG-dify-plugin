# 数据库支持扩展更新

## 概述

本次更新扩展了 SchemaRAG 插件对多种数据库类型的支持，从原来只支持 MySQL 和 PostgreSQL 扩展到支持 6 种数据库类型。

## 支持的数据库类型

| 数据库类型 | 默认端口 | 驱动程序 | 连接字符串格式 |
|------------|----------|----------|----------------|
| MySQL | 3306 | pymysql | `mysql+pymysql://user:password@host:port/database` |
| PostgreSQL | 5432 | psycopg2-binary | `postgresql://user:password@host:port/database` |
| Microsoft SQL Server | 1433 | pymssql | `mssql+pymssql://user:password@host:port/database` |
| Oracle | 1521 | cx-Oracle | `oracle+cx_Oracle://user:password@host:port/database` |
| 达梦数据库 | 5236 | dm+pymysql | `dm+pymysql://user:password@host:port/database` |

## 更新的文件

### 1. `provider/provider.yaml`

- **添加了新的数据库类型选项**：
  - SQLite
  - Microsoft SQL Server
  - Oracle
  - 达梦数据库（Dameng）

- **更新了端口配置**：
  - 为不同数据库类型提供了相应的默认端口信息
  - 更新了占位符文本，帮助用户了解各数据库的默认端口

- **更新了字段说明**：
  - 针对 SQLite 数据库，在相关字段中添加了说明（SQLite 不需要主机、端口、用户名、密码）

### 2. `provider/build_schema_rag.py`

- **添加了 `_get_default_port()` 方法**：
  - 根据数据库类型自动返回对应的默认端口
  - 支持所有 6 种数据库类型

- **更新了凭据验证逻辑**：
  - 对 SQLite 数据库进行特殊处理
  - SQLite 只需要验证数据库名称（文件路径）
  - 其他数据库类型需要完整的连接信息

- **更新了数据库配置创建逻辑**：
  - 自动使用正确的默认端口
  - 对 SQLite 使用合适的默认值

### 3. `core/m_schema/schema_engine.py`

- **更新了 `init_mschema()` 方法**：
  - 添加了对 SQLite、MSSQL、Oracle 和达梦数据库的支持
  - 正确处理不同数据库的 schema 命名规则
  - SQLite 不使用 schema
  - SQL Server、Oracle 和达梦数据库的 schema 处理逻辑

### 4. `requirements.txt` 和 `pyproject.toml`

- **添加了新的数据库驱动程序**：
  - `pymssql` - Microsoft SQL Server 驱动
  - `cx-Oracle` - Oracle 数据库驱动
  - `dameng-python` - 达梦数据库驱动（已注释，按需启用）


### 端口自动选择

当用户没有指定端口时，插件会根据数据库类型自动选择合适的默认端口：

```python
def _get_default_port(self, db_type: str) -> int:
    port_mapping = {
        "mysql": 3306,
        "postgresql": 5432,
        "mssql": 1433,
        "oracle": 1521,
        "dameng": 5236,
        "sqlite": 0,  # SQLite 不需要端口
    }
    return port_mapping.get(db_type, 3306)
```

## 测试

创建了 `test_database_support.py` 脚本来验证所有数据库类型的连接字符串生成是否正确。测试结果显示所有 6 种数据库类型都能正确生成连接字符串。

## 使用方式

用户在配置插件时：

1. 选择相应的数据库类型
2. 填写对应的连接信息
3. 对于 SQLite，只需要填写数据库文件路径，其他字段可以随意填写（因为不会被使用）
4. 对于其他数据库，按照标准的连接信息填写

插件会自动根据数据库类型进行适配和处理。
