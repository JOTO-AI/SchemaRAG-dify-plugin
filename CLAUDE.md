# CLAUDE.md - AI Assistant Guide for SchemaRAG Dify Plugin

## Project Overview

SchemaRAG is a **Dify plugin** that automates database schema analysis and enables natural language to SQL query conversion. It provides intelligent database querying capabilities for the Dify platform.

- **Type:** Tool Provider Plugin for Dify
- **Version:** 0.1.6
- **Language:** Python 3.12+
- **License:** Apache-2.0
- **Author:** joto (JOTO-AI)

### Core Functionality
- Multi-database schema extraction and indexing
- Natural language to SQL conversion (Text2SQL)
- SQL execution with safety controls
- LLM-based data analysis and visualization
- SQL auto-repair with LLM feedback

---

## Project Structure

```
SchemaRAG-dify-plugin/
├── core/                       # Core business logic
│   ├── dify/                   # Dify client integration
│   ├── llm_plot/               # LLM-based chart generation
│   └── m_schema/               # Schema metadata handling
│       ├── schema_engine.py    # Database schema extraction
│       ├── m_schema.py         # Metadata representation
│       └── sql_database.py     # Base database abstraction
├── service/                    # Service layer
│   ├── cache/                  # Caching (LRU, TTL)
│   │   ├── cache_manager.py    # Cache singleton manager
│   │   └── utils.py            # Cache utilities
│   ├── context/                # Context/conversation management
│   ├── database_service.py     # SQLAlchemy database operations
│   ├── dify_service.py         # Dify API integration
│   ├── knowledge_service.py    # Knowledge base retrieval
│   ├── schema_builder.py       # Schema generation & upload
│   ├── sql_refiner.py          # SQL auto-correction service
│   └── network_service.py      # Network operations
├── tools/                      # Dify tool implementations
│   ├── text2sql.py             # Natural language to SQL
│   ├── text2data.py            # End-to-end NL to data
│   ├── sql_executer.py         # SQL execution tool
│   ├── sql_executer_cust.py    # Custom DB SQL executor
│   ├── data_summary.py         # Data analysis tool
│   ├── llm_plot.py             # Chart generation tool
│   ├── parameter_validator.py  # Input validation
│   └── *.yaml                  # Tool configurations
├── provider/                   # Plugin provider
│   ├── build_schema_rag.py     # Provider implementation
│   └── provider.yaml           # Provider configuration
├── prompt/                     # Prompt templates
│   └── components/             # Modular prompt components
├── test/                       # Test suite (pytest)
├── demo/                       # Example workflows
├── docs/                       # Documentation
├── config.py                   # Configuration dataclasses
├── main.py                     # Plugin entry point
├── utils.py                    # Utility functions
├── manifest.yaml               # Dify plugin manifest
├── pyproject.toml              # Project metadata
├── requirements.txt            # Dependencies
└── uv.lock                     # Locked dependencies
```

---

## Development Setup

### Prerequisites
- Python 3.12+
- `uv` package manager (recommended)

### Running Locally
```bash
# Install dependencies
uv sync

# Run the plugin
uv run main.py
```

### Debug Configuration
Copy `.env.example` to `.env` and configure:
```
INSTALL_METHOD=remote
REMOTE_INSTALL_URL=<plugin-daemon-url>
REMOTE_INSTALL_KEY=<debug-key-from-dify>
```

---

## Supported Databases

| Database | Port | Driver | SQLAlchemy URI Format |
|----------|------|--------|-----------------------|
| MySQL | 3306 | `pymysql` | `mysql+pymysql://user:pass@host:port/db` |
| PostgreSQL | 5432 | `psycopg2` | `postgresql+psycopg2://user:pass@host:port/db` |
| SQL Server | 1433 | `pymssql` | `mssql+pymssql://user:pass@host:port/db` |
| Oracle | 1521 | `oracledb` | `oracle+oracledb://user:pass@host:port/?service_name=db` |
| DamengDB | 5236 | `dmPython` | `dm+dmPython://user:pass@host:port/db` |
| Doris | - | `mysql` | `doris+mysql://user:pass@host:port/db` |

---

## Key Technologies

- **Dify SDK:** `dify-plugin` for plugin infrastructure
- **Database:** SQLAlchemy ORM with multiple drivers
- **Data Processing:** pandas, tabulate, openpyxl
- **HTTP Client:** httpx (async support)
- **Validation:** pydantic v2
- **Testing:** pytest

---

## Coding Conventions

### Language
- Code comments and docstrings are primarily in **Chinese**
- Public API documentation and error messages support multilingual (en_US, zh_Hans, pt_BR)
- Use Chinese for internal logging

### Code Style
```python
# Module docstring at top
"""
项目配置模块
"""

# Imports order: stdlib, third-party, local
import os
from typing import Dict, List, Optional
from sqlalchemy import create_engine
from service.database_service import DatabaseService

# Class-level constants in UPPER_SNAKE_CASE
class MyTool(Tool):
    DEFAULT_TOP_K = 5
    MAX_CONTENT_LENGTH = 10000
    _cache_max_size = 10  # Private with underscore

    def __init__(self):
        """初始化说明"""
        self._private_var = None

    @property
    def some_property(self):
        """延迟初始化的属性，使用缓存避免重复创建"""
        pass

    def _private_method(self):
        """私有方法使用下划线前缀"""
        pass
```

### Type Hints
- Use type hints for function parameters and return values
- Use `Optional[]` for nullable types
- Use `Dict`, `List`, `Tuple` from typing module

### Error Handling
```python
try:
    # Operation
    pass
except ValueError as e:
    self.logger.error(f"参数验证错误: {str(e)}")
    raise ValueError(f"参数错误: {str(e)}")
except ConnectionError as e:
    self.logger.error(f"网络连接错误: {str(e)}")
    raise
except Exception as e:
    self.logger.error(f"异常: {str(e)}")
    raise ValueError(f"操作异常: {str(e)}")
```

### Logging
```python
import logging
from dify_plugin.config.logger_format import plugin_logger_handler

self.logger = logging.getLogger(__name__)
self.logger.addHandler(plugin_logger_handler)

self.logger.info(f"从知识库 {dataset_id} 检索架构信息")
self.logger.warning("未检索到相关的架构信息")
self.logger.error(f"SQL生成异常: {str(e)}")
```

---

## Tool Development Pattern

### Tool Structure (tools/*.py)
```python
from collections.abc import Generator
from typing import Any
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

class MyTool(Tool):
    # Class-level constants
    DEFAULT_VALUE = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Access credentials
        self.api_key = self.runtime.credentials.get("api_key")
        self._validate_config()

    def _validate_config(self):
        """验证配置"""
        pass

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        """Main tool execution - implements generator pattern"""
        # 1. Validate parameters
        # 2. Execute business logic
        # 3. Yield results
        yield self.create_text_message(text="Result")
```

### Tool Configuration (tools/*.yaml)
```yaml
identity:
  name: my_tool
  author: joto
  label:
    en_US: My Tool
    zh_Hans: 我的工具
description:
  human:
    en_US: Tool description for humans
    zh_Hans: 工具描述
  llm: Description for LLM to understand when to use this tool
parameters:
  - name: param_name
    type: string
    required: true
    label:
      en_US: Parameter Name
      zh_Hans: 参数名称
    human_description:
      en_US: Description
      zh_Hans: 描述
```

---

## Testing Guidelines

### Test Location
Tests are in `/test/` directory using pytest.

### Test Pattern
```python
import unittest
from unittest.mock import Mock, MagicMock, patch

class TestMyFeature(unittest.TestCase):
    """功能测试类"""

    def setUp(self):
        """测试前准备"""
        self.mock_service = Mock()

    def test_feature_success(self):
        """测试成功场景"""
        pass

    def test_feature_failure(self):
        """测试失败场景"""
        pass
```

### Running Tests
```bash
# Run all tests
uv run pytest test/

# Run specific test file
uv run pytest test/test_sql_refiner.py

# Run with verbose output
uv run pytest -v test/
```

---

## Git Commit Conventions

Commits follow a Chinese-style format with conventional prefixes:

```
feat: 添加新功能描述
fix: 修复问题描述
refactor: 重构代码描述
docs: 更新文档描述
test: 添加测试描述
```

### Examples from History
```
feat: 更新版本号至0.1.6，优化文档和元数据描述
feat: 优化SQL执行器和工具，重构缓存机制，增强SQL清理与验证功能
feat: 添加SQL自动纠错服务和相关测试用例，集成LLM反馈机制以修复SQL错误
fix: 修正示例工作流下载链接，确保指向正确的路径
```

---

## CI/CD Workflows

### Plugin Publishing (`.github/workflows/plugin-publish.yml`)
Triggered on GitHub release:
1. Downloads `dify-plugin` CLI tool
2. Extracts metadata from `manifest.yaml`
3. Packages plugin as `.difypkg`
4. Creates PR to `langgenius/dify-plugins`

### Version Updates
When releasing a new version:
1. Update `version` in `manifest.yaml`
2. Update `version` in `pyproject.toml`
3. Update `meta.version` in `manifest.yaml`
4. Update version badge in `README.md`

---

## Key Files to Know

| File | Purpose |
|------|---------|
| `manifest.yaml` | Plugin metadata, permissions, resources |
| `provider/provider.yaml` | Credentials schema, tool registrations |
| `config.py` | Database and Dify configuration dataclasses |
| `main.py` | Plugin entry point |
| `tools/*.yaml` | Tool parameter definitions |
| `prompt/` | LLM prompt templates |

---

## Security Considerations

- **SELECT-only:** SQL executor tools only allow SELECT queries
- **URL encoding:** Passwords with special characters are URL-encoded
- **Row limits:** Query results have configurable max row limits
- **Field whitelist:** Optional table/column filtering
- **No credentials in logs:** Cache keys exclude passwords

---

## Common Development Tasks

### Adding a New Tool
1. Create `tools/my_tool.py` implementing `Tool` class
2. Create `tools/my_tool.yaml` with parameters and labels
3. Register in `provider/provider.yaml` under `extra.python.source`
4. Add tests in `test/test_my_tool.py`

### Adding Database Support
1. Add driver to `pyproject.toml` dependencies
2. Add mapping in `DatabaseService.DB_DRIVERS`
3. Add connection string format in `config.py`
4. Update `provider.yaml` database type options

### Updating Prompts
Prompts are in `prompt/` directory. Key files:
- `text2sql_prompt.py` - SQL generation prompts
- `components/` - Reusable prompt components

---

## Architecture Patterns

### Caching Strategy
- **LRU Cache:** Service instances (max 10)
- **TTL Cache:** SQL query results (2 hours)
- **Cache Manager:** Singleton pattern via `CacheManager.get_instance()`

### Service Layer Pattern
```
Provider → Tool → Service → Database/API
              ↓
         Validator
```

### Context Management
- `ContextManager` stores conversation history
- Per-user context with configurable window size
- Memory can be reset via `reset_memory` parameter

---

## Troubleshooting

### Common Issues

**Import errors:**
- Ensure project root is in Python path
- Check `sys.path.insert(0, project_root)` pattern

**Database connection failures:**
- Verify URL encoding for special characters in passwords
- Check driver installation for specific database types

**Plugin not loading:**
- Verify `manifest.yaml` syntax
- Check Python version >= 3.12
- Ensure all YAML tool files are valid
