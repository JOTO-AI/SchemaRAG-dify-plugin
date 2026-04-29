# AGENTS.md - AI Assistant Guide for SchemaRAG Dify Plugin

This file is the operating guide for AI agents working in this repository. Follow it together with the user's latest request and the repository's existing code style.

## Project Overview

SchemaRAG is a **Dify tool provider plugin** that automates database schema extraction, uploads schema dictionaries to Dify Knowledge Bases, and provides natural-language-to-SQL tools for Dify Chatflow / Workflow / Agent applications.

- **Type:** Dify Tool Provider Plugin
- **Version:** 0.1.7
- **Runtime:** Python 3.12+ in Dify plugin runner
- **License:** Apache-2.0
- **Author:** joto (JOTO-AI)

### Core Functionality

- Multi-database schema extraction and indexing
- Schema dictionary upload to Dify Knowledge Bases
- Natural language to SQL conversion
- SQL execution with safety controls
- LLM-based data analysis and visualization
- SQL auto-repair with LLM feedback

## Official Dify References

When changing plugin behavior, validate assumptions against the current official Dify docs first:

- Tool plugin development: <https://docs.dify.ai/en/develop-plugin/dev-guides-and-walkthroughs/tool-plugin>
- Manifest specification: <https://docs.dify.ai/en/develop-plugin/features-and-specs/plugin-types/plugin-info-by-manifest>
- List Knowledge Bases: <https://docs.dify.ai/api-reference/datasets/get-knowledge-base-list>
- Create Knowledge Base: <https://docs.dify.ai/api-reference/knowledge-bases/create-an-empty-knowledge-base>
- Create Document by Text: <https://docs.dify.ai/api-reference/documents/create-document-by-text>
- Create Document by File: <https://docs.dify.ai/api-reference/documents/create-document-by-file>

Important current API facts:

- Knowledge Base list endpoint is `GET /datasets`, with paginated response fields such as `data`, `has_more`, `limit`, and `total`.
- Knowledge Base creation endpoint is `POST /datasets`; duplicate names can return HTTP 409.
- Document upload endpoints use hyphenated paths:
  - `POST /datasets/{dataset_id}/document/create-by-text`
  - `POST /datasets/{dataset_id}/document/create-by-file`
- Knowledge Base API requests require `Authorization: Bearer {API_KEY}`.

## Repository Structure

```
SchemaRAG-dify-plugin/
├── core/
│   ├── dify/                   # Low-level Dify HTTP clients
│   ├── llm_plot/               # Chart generation and data analysis helpers
│   └── m_schema/               # Schema metadata extraction and representation
├── service/
│   ├── cache/                  # LRU / TTL cache implementations
│   ├── context/                # Conversation memory
│   ├── database_service.py     # SQLAlchemy execution layer
│   ├── dify_service.py         # Dify Knowledge Base upload workflow
│   ├── knowledge_service.py    # Knowledge Base retrieval
│   ├── schema_builder.py       # Schema dictionary generation and upload
│   └── sql_refiner.py          # SQL auto-repair
├── tools/                      # Dify tool implementations and YAML descriptors
├── provider/                   # Tool provider YAML and credential validation
├── prompt/                     # Prompt templates
├── test/                       # pytest / unittest tests
├── docs/                       # Project docs
├── manifest.yaml               # Dify plugin manifest
├── main.py                     # Dify plugin entry point
├── pyproject.toml              # Python package metadata
├── requirements.txt            # Plugin/package requirements fallback
└── uv.lock                     # Locked dependencies
```

## Agent Operating Rules

- Inspect `git status --short` before editing. This workspace may contain unrelated user changes.
- Never revert, overwrite, stage, commit, or format unrelated changes unless the user explicitly asks.
- Never commit secrets. In particular, `.env`, `.env.example`, remote install keys, database passwords, and dataset API keys must not be committed.
- Prefer narrow, behavior-focused changes. Do not bundle release version bumps, README rewrites, or manifest edits into bugfix PRs unless requested.
- Use `rg` / `rg --files` for searching.
- Use `apply_patch` for manual file edits.
- Keep comments and logs primarily in Chinese, matching the existing codebase.
- Preserve Dify plugin compatibility before making convenience refactors.

## Development Setup

### Prerequisites

- Python 3.12+
- `uv`
- A Dify instance and plugin debug key for remote debugging

### Local Commands

```bash
# Install / sync dependencies
uv sync

# Run the plugin for remote debugging
uv run main.py

# Run focused tests
uv run --no-sync pytest test/test_dify_client.py test/test_dify_service.py
```

Use `uv run --no-sync` for focused tests after dependencies are already installed. This avoids unnecessary dependency resolution while working on code.

### Debug Configuration

Copy `.env.example` to `.env` and put real debug credentials only in `.env`:

```env
INSTALL_METHOD=remote
REMOTE_INSTALL_URL=<plugin-daemon-url>
REMOTE_INSTALL_KEY=<debug-key-from-dify>
```

Do not replace placeholders in `.env.example` with real credentials.

## Dify Plugin Rules

### Manifest

`manifest.yaml` must remain YAML-valid. Dify packaging can fail if this file is malformed.

Current plugin permissions are intentional:

- `tool.enabled: true`
- `model.enabled: true`, `llm: true`
- `storage.enabled: true`
- `app.enabled: false`

Only add permissions when a feature truly needs them, and explain why in the PR.

### Provider YAML

`provider/provider.yaml` defines:

- provider identity and labels
- `credentials_for_provider`
- supported app types
- tool YAML registrations
- Python provider entrypoint under `extra.python`

When adding or changing credentials:

- Use `secret-input` for API keys, passwords, and tokens.
- Keep labels / descriptions multilingual when nearby fields are multilingual.
- Keep `tools:` aligned with actual files under `tools/`.

### Provider Credential Validation

`provider/build_schema_rag.py` implements `ToolProvider`.

Rules:

- `_validate_credentials(credentials)` must either return `None` on success or raise `ToolProviderCredentialValidationError` on validation failure.
- Do not leak passwords, dataset API keys, or debug keys in errors or logs.
- If validation performs side effects, such as schema generation and upload, every external failure must be converted to `ToolProviderCredentialValidationError`.
- Keep root-cause information in the message, but avoid sensitive values.

### Tool Implementations

Tools under `tools/*.py` inherit from `dify_plugin.Tool`.

Rules:

- Implement `_invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]`.
- Yield Dify messages using helpers such as `create_text_message` or `create_json_message`.
- Validate parameters before calling services.
- Keep LLM calls inside tool runtime paths, not provider validation.
- Use `self.runtime.credentials` for provider credentials and never hard-code credentials.

### Tool YAML

Each tool YAML should include:

- `identity`
- `description.human`
- `description.llm`
- `parameters`
- `form: llm` for LLM-inferred parameters
- `form: form` for UI-configured parameters

When adding parameters:

- Include `label`, `human_description`, and `llm_description`.
- Use `select` with explicit `options` for finite modes.
- Use `model-selector` for model choices.
- Keep defaults conservative.

## Dify Knowledge Base API Rules

The project uses `core/dify/dify_client.py` and `service/dify_service.py` to create/find Knowledge Bases and upload schema documents.

Rules:

- Use the configured `api_uri` as the base URL, normally ending in `/v1`.
- Use `Authorization: Bearer <dataset_api_key>`.
- Use `httpx.Client(timeout=30.0, trust_env=False)` for Dify API calls. This prevents internal Dify hosts such as `192.168.*` from being routed through system proxy variables.
- When finding a Knowledge Base by name, scan all pages from `GET /datasets`; do not assume the target is on page 1.
- On `POST /datasets` HTTP 409, retry paginated lookup before reporting failure.
- Use official hyphenated document endpoints: `create-by-text`, `create-by-file`, `update-by-text`, and `update-by-file`.
- `create-by-text` and `create-by-file` are asynchronous and return a `batch`; do not assume indexing is complete immediately unless code explicitly checks indexing status.
- Preserve readable API error messages. Do not wrap known HTTP status errors into vague "unknown error" messages.

## Supported Databases

| Database | Port | Driver | SQLAlchemy URI Format |
|----------|------|--------|-----------------------|
| MySQL | 3306 | `pymysql` | `mysql+pymysql://user:pass@host:port/db` |
| PostgreSQL | 5432 | `psycopg2-binary` | `postgresql+psycopg2://user:pass@host:port/db` |
| SQL Server | 1433 | `pymssql` | `mssql+pymssql://user:pass@host:port/db` |
| Oracle | 1521 | `oracledb` | `oracle+oracledb://user:pass@host:port/?service_name=db` |
| DamengDB | 5236 | `dmPython` + `dmSQLAlchemy` | `dm+dmPython://user:pass@host:port` with schema switch |
| Doris | 9030 | `pymysql` / Doris dialect | `doris+pymysql://user:pass@host:port/db` |

Database rules:

- URL-encode usernames and passwords in connection strings.
- Keep database credentials out of logs and cache keys.
- SQL execution tools must enforce SELECT-only behavior where intended.
- Result row limits must stay configurable and bounded.
- Dameng dependencies are platform-limited. `dmpython` and `dmsqlalchemy` must not be mandatory on macOS because wheels are unavailable there.
- Do not add source-build `psycopg2`; keep `psycopg2-binary` unless there is a deliberate deployment reason and a matching CI change.

## Architecture Boundaries

Follow the existing flow:

```
Provider -> Tool -> Service -> Database / Dify API
              |
              v
          Validators
```

Boundary rules:

- `provider/`: credential validation, provider setup, high-level orchestration.
- `tools/`: Dify tool entrypoints, parameter validation, runtime output.
- `service/`: business workflows such as schema build, upload, SQL execution, retrieval, and repair.
- `core/dify/`: low-level Dify HTTP client only.
- `core/m_schema/`: database schema extraction and metadata representation.
- `prompt/`: prompt construction only.

Avoid moving HTTP request details into tools or provider code. Avoid placing Dify runtime concerns inside database schema extraction classes.

## Coding Conventions

### Language

- Internal comments, docstrings, and logs are primarily Chinese.
- Public labels and descriptions should keep existing multilingual style: `en_US`, `zh_Hans`, `pt_BR`, and any existing locales nearby.
- Error messages shown to users should be actionable and not expose secrets.

### Style

```python
"""
项目配置模块
"""

import os
from typing import Dict, List, Optional

from sqlalchemy import create_engine

from service.database_service import DatabaseService


class MyTool(Tool):
    DEFAULT_TOP_K = 5
    MAX_CONTENT_LENGTH = 10000
    _cache_max_size = 10

    def __init__(self, *args, **kwargs):
        """初始化工具"""
        super().__init__(*args, **kwargs)
```

Rules:

- Use type hints for function parameters and return values.
- Prefer `Optional`, `Dict`, `List`, and `Tuple` consistently with the existing code.
- Keep class-level constants in `UPPER_SNAKE_CASE`.
- Use private method prefixes for internal helpers.
- Add comments only where they explain non-obvious behavior.

### Logging

```python
import logging
from dify_plugin.config.logger_format import plugin_logger_handler

logger = logging.getLogger(__name__)
logger.addHandler(plugin_logger_handler)
```

Rules:

- Log important state transitions: schema generation, Dify upload, SQL execution, retries, and cache hits.
- Never log passwords, API keys, tokens, or full connection strings.
- Prefer root-cause messages over generic "unknown error".

## Dependency Rules

Maintain dependency declarations in both `pyproject.toml` and `requirements.txt` when applicable.

Current constraints:

- `dify-plugin` is required for plugin runtime.
- `pymysql`, `psycopg2-binary`, `pymssql`, and `oracledb` support the main database drivers.
- `dmpython` and `dmsqlalchemy` must use platform markers for Linux/Windows only.
- `uv.lock` must be refreshed when `pyproject.toml` dependencies change.

After dependency edits, run:

```bash
uv lock
uv run --no-sync pytest test/test_dependency_metadata.py
```

## Testing Guidelines

Tests live under `test/` and currently use `pytest` with many `unittest.TestCase` classes.

### Test Naming

- `test_dify_client.py`: low-level Dify HTTP client behavior and endpoint paths.
- `test_dify_service.py`: Knowledge Base upload workflow, dataset lookup, pagination, conflict handling.
- `test_provider_credentials.py`: provider credential validation and Dify SDK error types.
- `test_dependency_metadata.py`: platform-specific dependency metadata.
- `test_sql_refiner.py`: SQL repair behavior.
- `test_context_manager.py`: conversation memory behavior.

### Required Tests by Change Type

| Change Type | Minimum Test Command |
|-------------|----------------------|
| Dify HTTP client paths/proxy/errors | `uv run --no-sync pytest test/test_dify_client.py` |
| Knowledge Base upload / dataset lookup | `uv run --no-sync pytest test/test_dify_service.py` |
| Provider credential validation | `uv run --no-sync pytest test/test_provider_credentials.py` |
| Dependency metadata | `uv run --no-sync pytest test/test_dependency_metadata.py` |
| SQL repair | `uv run --no-sync pytest test/test_sql_refiner.py` |
| General sanity | `uv run --no-sync pytest test/` |

When fixing a bug, add or update a regression test first when feasible. Run the test red, implement the fix, then run it green.

## Security Considerations

- Do not commit `.env` or real debug credentials.
- Keep `.env.example` placeholder-only.
- Use `secret-input` for sensitive provider credentials.
- Do not print database passwords or dataset API keys.
- Cache keys must exclude passwords.
- SQL execution tools must reject dangerous statements when designed as query-only tools.
- Respect optional table and column whitelists.
- Treat Dify Dataset API keys as server-side secrets.

## Common Development Tasks

### Adding a New Tool

1. Create `tools/my_tool.py` implementing `Tool`.
2. Create `tools/my_tool.yaml`.
3. Register the YAML in `provider/provider.yaml`.
4. Add or update provider imports only if the provider needs to return the tool class.
5. Add focused tests under `test/`.
6. Run the relevant pytest command.

### Adding Database Support

1. Add the driver dependency with platform markers if the package is not universal.
2. Add mapping in `DatabaseService.DB_DRIVERS`.
3. Add connection string logic in `config.py`.
4. Add SQLAlchemy engine args if required.
5. Update `provider/provider.yaml` database type options.
6. Add connection-string and metadata tests.

### Updating Dify Knowledge Base Behavior

1. Check the official Dify API reference first.
2. Update `core/dify/dify_client.py` for low-level endpoint or HTTP behavior.
3. Update `service/dify_service.py` for upload workflow behavior.
4. Add tests in `test/test_dify_client.py` and/or `test/test_dify_service.py`.
5. Verify with focused tests and, if possible, remote plugin debugging.

### Updating Prompts

- Prompt templates live in `prompt/`.
- Keep prompt-building helpers deterministic and testable.
- Preserve dialect-specific behavior.
- Add tests when prompt structure changes affect tool output.

## Git and PR Rules

- Before staging, run `git status --short`.
- Stage explicit files only in mixed worktrees.
- Do not stage `.env.example` if it contains real local values.
- Do not stage version bumps unless the user requested a release/version update.
- Use Chinese conventional commit prefixes:

```text
feat: 添加新功能描述
fix: 修复问题描述
refactor: 重构代码描述
docs: 更新文档描述
test: 添加测试描述
```

Before commit or PR:

```bash
uv run --no-sync pytest <relevant tests>
git diff --cached --check
```

## Release and Version Updates

When releasing a new version, update all relevant version surfaces together:

1. `manifest.yaml` top-level `version`
2. `manifest.yaml` `meta.version`
3. `pyproject.toml` project `version`
4. `README.md` version badge and text
5. `README_CN.md` version badge and text
6. Any project guide that explicitly states the current version

Do not perform these version updates as part of an unrelated bugfix.

## Troubleshooting

### Authorization Fails During Provider Validation

Check:

- `_validate_credentials` raises `ToolProviderCredentialValidationError`, not raw `ValueError`.
- Dify API errors preserve useful messages.
- Schema generation succeeded before upload.
- Dataset API key is a Knowledge Base API key.
- No secrets are printed in logs.

### Dify API Returns 502 or Timeout for Internal IPs

Check:

- `core/dify/dify_client.py` uses `httpx.Client(..., trust_env=False)`.
- The base URL includes `/v1`.
- The Dify host is reachable from the plugin process.
- The request did not go through an HTTP proxy.

### Dataset Already Exists but Cannot Be Found

Check:

- `service/dify_service.py` paginates `GET /datasets`.
- 409 from `POST /datasets` triggers another paginated lookup.
- The API key has permission to list the target Knowledge Base.
- The dataset name is exact and within Dify's name constraints.

### Document Upload Fails with 404 or 405

Check:

- Use `create-by-text` / `create-by-file`, not `create_by_text` / `create_by_file`.
- `client.dataset_id` is set before uploading.
- `process_rule` matches Dify's current API shape.

### Dependency Install Fails on macOS arm64

Check:

- `dmpython` and `dmsqlalchemy` have Linux/Windows platform markers.
- `psycopg2` source package is not declared.
- `psycopg2-binary` is present.
- `uv.lock` has been refreshed after metadata changes.

### Plugin Does Not Load

Check:

- `manifest.yaml` is valid YAML.
- `provider/provider.yaml` references existing tool YAML files.
- Python version is compatible with the Dify plugin runner.
- `extra.python.source` and provider class name are correct.

## Final Checklist for Agents

Before saying a fix is complete:

- Read the relevant code path and official Dify docs if the behavior touches Dify APIs.
- Add or update regression tests for the bug.
- Run focused tests and report the exact command.
- Run `git diff --check` or `git diff --cached --check` for the files in scope.
- State any skipped tests or environment blockers honestly.
- Mention unrelated dirty files that were intentionally left untouched.
