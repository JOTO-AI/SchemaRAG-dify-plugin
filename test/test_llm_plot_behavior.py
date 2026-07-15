#!/usr/bin/env python3
"""
测试 LLM 绘图模块的数据转换、参数校验和 API 响应处理
"""

from unittest.mock import Mock, patch

import pytest
import requests

from core.llm_plot.chart_generator import ChartGenerator
from core.llm_plot.config import ChartConfig
from core.llm_plot.data_processor import DataProcessor
from core.llm_plot.models import ChartRecommendation
from core.llm_plot.validator import ParameterValidator


def test_line_data_transform_converts_comma_numbers_and_skips_null_values():
    """折线图数据转换应处理千分位字符串并跳过空值。"""
    data = [
        {"month": "Jan", "amount": "1,200.50"},
        {"month": "Feb", "amount": None},
        {"month": None, "amount": 100},
        {"month": "Mar", "amount": 1500},
    ]

    result = DataProcessor.transform_data_for_chart(
        "line",
        data,
        x_field="month",
        y_field="amount",
    )

    assert result == [
        {"time": "Jan", "value": 1200.50},
        {"time": "Mar", "value": 1500.0},
    ]


def test_histogram_data_transform_extracts_numeric_values():
    """直方图数据转换应提取指定数值字段。"""
    result = DataProcessor.transform_data_for_chart(
        "histogram",
        [{"score": "1,000"}, {"score": 25.5}, {"score": None}],
        x_field="ignored",
        y_field="score",
    )

    assert result == [1000.0, 25.5]


def test_pie_data_transform_counts_categories_when_y_field_missing():
    """饼图未提供 y 字段时应按分类计数。"""
    result = DataProcessor.transform_data_for_chart(
        "pie",
        [
            {"brand": "A"},
            {"brand": "A"},
            {"brand": "B"},
            {"brand": ""},
        ],
        x_field="brand",
    )

    assert result == [
        {"category": "A", "value": 2},
        {"category": "B", "value": 1},
    ]


def test_data_transform_reports_missing_fields_with_available_columns():
    """字段缺失错误应包含缺失字段和可用字段，便于用户修正。"""
    with pytest.raises(ValueError) as context:
        DataProcessor.transform_data_for_chart(
            "line",
            [{"month": "Jan", "amount": 1}],
            x_field="month",
            y_field="sales",
        )

    assert "sales" in str(context.value)
    assert "month, amount" in str(context.value)


def test_data_processor_clean_data_and_summary():
    """数据清洗和摘要应过滤全空记录并保留字段信息。"""
    cleaned = DataProcessor.clean_data(
        [
            {},
            {"id": None, "name": None},
            {"id": 1, "name": None},
        ]
    )

    assert cleaned == [{"id": 1, "name": None}]
    assert DataProcessor.get_data_summary(cleaned) == {
        "record_count": 1,
        "fields": ["id", "name"],
        "sample": {"id": 1, "name": None},
    }
    assert DataProcessor.get_data_summary([]) == {
        "record_count": 0,
        "fields": [],
        "sample": None,
    }


def test_chart_config_deep_merge_and_template_selection():
    """图表配置合并应保留基础主题并覆盖模板/自定义字段。"""
    config = ChartConfig.create_chart_config(
        "histogram",
        data=[1, 2, 3],
        title="分数分布",
        x_title="分数",
        y_title="人数",
        style={"lineWidth": 4},
        binNumber=6,
    )

    assert config["type"] == "histogram"
    assert config["theme"] == "academy"
    assert config["title"] == "分数分布"
    assert config["axisXTitle"] == "分数"
    assert config["axisYTitle"] == "人数"
    assert config["style"]["backgroundColor"] == "#ffffff"
    assert config["style"]["lineWidth"] == 4
    assert config["binNumber"] == 6


def test_chart_generator_histogram_config_uses_bounded_bin_count():
    """直方图配置应根据数据量生成有界 binNumber。"""
    generator = ChartGenerator()
    recommendation = ChartRecommendation(
        chart_type="histogram",
        x_field="score",
        y_field="score",
        title="分数分布",
        description="数值分布适合直方图",
    )
    data = [{"score": value} for value in range(60)]

    config = generator.generate_chart_config(recommendation, data)

    assert config["type"] == "histogram"
    assert config["binNumber"] == 10
    assert config["axisXTitle"] == "score区间"
    assert config["data"] == [float(value) for value in range(60)]


def test_parameter_validator_accepts_valid_parameters_and_rejects_bad_inputs():
    """绘图参数验证应覆盖必填、JSON 格式、图表类型和字段存在性。"""
    valid_parameters = {
        "user_question": "画销售趋势",
        "sql_query": "select month, amount from sales",
        "data": '[{"month":"Jan","amount":1}]',
        "llm": {"model": "gpt-test"},
    }

    ParameterValidator.validate_parameters(valid_parameters)
    ParameterValidator.validate_chart_type("line")
    ParameterValidator.validate_field_exists(
        [{"month": "Jan", "amount": 1}],
        "amount",
    )

    with pytest.raises(ValueError, match="参数不能为空: sql_query"):
        ParameterValidator.validate_parameters(valid_parameters | {"sql_query": None})

    with pytest.raises(ValueError, match="有效的 JSON"):
        ParameterValidator.validate_data_format("{bad json")

    with pytest.raises(ValueError, match="无效的图表类型"):
        ParameterValidator.validate_chart_type("scatter")

    with pytest.raises(ValueError, match="字段 'missing' 不存在"):
        ParameterValidator.validate_field_exists([{"field": 1}], "missing")


def test_generate_chart_url_success_and_error_responses():
    """AntV API 成功响应返回 URL，业务失败响应抛出可读错误。"""
    generator = ChartGenerator()
    success = Mock()
    success.json.return_value = {
        "success": True,
        "resultObj": "https://example.com/chart.png",
    }

    with patch("core.llm_plot.chart_generator.requests.post", return_value=success):
        assert generator.generate_chart_url({"type": "pie", "data": []}) == (
            "https://example.com/chart.png"
        )

    failed = Mock()
    failed.json.return_value = {
        "success": False,
        "errorMessage": "bad chart config",
    }

    with patch("core.llm_plot.chart_generator.requests.post", return_value=failed):
        with pytest.raises(ValueError, match="bad chart config"):
            generator.generate_chart_url({"type": "pie", "data": []})


def test_generate_chart_url_handles_timeout_and_missing_result_object():
    """AntV API 超时和缺少 resultObj 时应抛出明确错误。"""
    generator = ChartGenerator()

    with patch(
        "core.llm_plot.chart_generator.requests.post",
        side_effect=requests.exceptions.Timeout,
    ):
        with pytest.raises(ValueError, match="请求 AntV API 超时"):
            generator.generate_chart_url({"type": "pie", "data": []})

    missing_url = Mock()
    missing_url.json.return_value = {"success": True}

    with patch("core.llm_plot.chart_generator.requests.post", return_value=missing_url):
        with pytest.raises(ValueError, match="未找到有效的图表 URL"):
            generator.generate_chart_url({"type": "pie", "data": []})
