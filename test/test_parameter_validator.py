#!/usr/bin/env python3
"""
测试工具参数验证与提取逻辑
"""

import logging

import pytest

from tools.parameter_validator import (
    validate_and_extract_sql_executer_parameters,
    validate_and_extract_text2sql_parameters,
)


VALID_TEXT2SQL_PARAMETERS = {
    "dataset_id": " dataset-1 ",
    "llm": {"provider": "openai", "model": "gpt-test"},
    "content": " 查询用户数量 ",
}


def test_text2sql_parameter_extraction_trims_values_and_applies_defaults():
    """Text2SQL 参数验证应清理空白并应用保守默认值。"""
    result = validate_and_extract_text2sql_parameters(VALID_TEXT2SQL_PARAMETERS)

    assert result == (
        "dataset-1",
        {"provider": "openai", "model": "gpt-test"},
        "查询用户数量",
        "mysql",
        5,
        "semantic_search",
        "",
        "",
        False,
        3,
        False,
        True,
    )


def test_text2sql_parameter_extraction_converts_optional_boolean_and_integer_values():
    """Text2SQL 参数验证应转换 select 字符串布尔值和数字字段。"""
    parameters = VALID_TEXT2SQL_PARAMETERS | {
        "dialect": "postgresql",
        "top_k": "12",
        "retrieval_model": "hybrid_search",
        "custom_prompt": " use strict SQL ",
        "example_dataset_id": " example-1 ",
        "memory_enabled": "true",
        "memory_window_size": "8",
        "reset_memory": "yes",
        "cache_enabled": "0",
    }

    result = validate_and_extract_text2sql_parameters(parameters)

    assert result[3] == "postgresql"
    assert result[4] == 12
    assert result[5] == "hybrid_search"
    assert result[6] == "use strict SQL"
    assert result[7] == "example-1"
    assert result[8] is True
    assert result[9] == 8
    assert result[10] is True
    assert result[11] is False


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"dataset_id": " "}, "缺少知识库ID"),
        ({"llm": None}, "缺少LLM模型配置"),
        ({"content": ""}, "缺少问题内容"),
        ({"dialect": "db2"}, "不支持的数据库方言: db2"),
        ({"top_k": "0"}, "top_k 必须在 1-50 之间"),
        ({"top_k": "abc"}, "top_k 必须是有效的整数"),
        ({"retrieval_model": "vector_only"}, "不支持的检索模型: vector_only"),
        ({"custom_prompt": 42}, "自定义提示词必须是字符串类型"),
        ({"example_dataset_id": 42}, "示例知识库ID必须是字符串类型"),
        ({"memory_window_size": "11"}, "memory_window_size 必须在 1-10 之间"),
    ],
)
def test_text2sql_parameter_validation_errors_are_actionable(override, message):
    """Text2SQL 参数错误应返回明确、面向用户的错误消息。"""
    assert validate_and_extract_text2sql_parameters(
        VALID_TEXT2SQL_PARAMETERS | override
    ) == message


def test_text2sql_parameter_validation_rejects_overlong_content():
    """问题内容超长时应明确报告限制和当前长度。"""
    result = validate_and_extract_text2sql_parameters(
        VALID_TEXT2SQL_PARAMETERS | {"content": "x" * 6},
        max_content_length=5,
    )

    assert result == "问题内容过长，最大允许 5 字符，当前 6 字符"


def test_sql_executer_parameter_extraction_success_path():
    """SQL 执行器参数验证应提取 SQL、输出格式和行数限制。"""
    result = validate_and_extract_sql_executer_parameters(
        {
            "sql": " SELECT * FROM users ",
            "output_format": "md",
            "max_line": "100",
        }
    )

    assert result == ("SELECT * FROM users", "md", 100, None)


@pytest.mark.parametrize(
    ("parameters", "message"),
    [
        ({}, "SQL查询不能为空"),
        ({"sql": "   "}, "SQL查询不能为空"),
        ({"sql": "select 1", "output_format": "csv"}, "输出格式只支持 'json' 或 'md'"),
    ],
)
def test_sql_executer_parameter_validation_errors(parameters, message):
    """SQL 执行器必要参数和格式错误应返回统一错误消息。"""
    assert validate_and_extract_sql_executer_parameters(parameters)[3] == message


def test_sql_executer_parameter_invalid_max_line_falls_back_to_default(caplog):
    """max_line 无效时应回退到默认值并记录警告。"""
    logger = logging.getLogger("test.sql_executer_parameters")

    with caplog.at_level(logging.WARNING):
        result = validate_and_extract_sql_executer_parameters(
            {"sql": "select 1", "max_line": "-1"},
            default_max_rows=500,
            logger=logger,
        )

    assert result == ("select 1", "json", 500, None)
    assert "max_line参数必须大于0" in caplog.text
