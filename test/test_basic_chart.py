"""
基本图表生成测试
测试 AntV 图表配置生成和 URL 提取逻辑
"""

from unittest.mock import Mock, patch

from core.llm_plot.chart_generator import ChartGenerator
from core.llm_plot.models import ChartRecommendation


def test_generate_line_chart_config():
    """测试折线图配置生成"""
    generator = ChartGenerator()
    recommendation = ChartRecommendation(
        chart_type="line",
        title="销售趋势",
        x_field="month",
        y_field="amount",
        description="时间序列适合折线图",
    )
    data = [
        {"month": "Jan", "amount": 10},
        {"month": "Feb", "amount": 15},
    ]

    config = generator.generate_chart_config(recommendation, data)

    assert config["type"] == "line"
    assert config["title"] == "销售趋势"
    assert config["axisXTitle"] == "month"
    assert config["axisYTitle"] == "amount"
    assert config["data"] == [
        {"time": "Jan", "value": 10.0},
        {"time": "Feb", "value": 15.0},
    ]


def test_generate_pie_chart_config():
    """测试饼图配置生成"""
    generator = ChartGenerator()
    recommendation = ChartRecommendation(
        chart_type="pie",
        title="市场份额",
        x_field="brand",
        y_field="share",
        description="占比数据适合饼图",
    )
    data = [
        {"brand": "华为", "share": 30},
        {"brand": "小米", "share": 25},
    ]

    config = generator.generate_chart_config(recommendation, data)

    assert config["type"] == "pie"
    assert config["title"] == "市场份额"
    assert config["data"] == [
        {"category": "华为", "value": 30},
        {"category": "小米", "value": 25},
    ]


def test_generate_chart_url_reads_antv_result_object():
    """测试从 AntV 响应中提取图表 URL"""
    generator = ChartGenerator()
    response = Mock()
    response.json.return_value = {
        "success": True,
        "resultObj": "https://example.com/chart.png",
    }

    with patch("core.llm_plot.chart_generator.requests.post", return_value=response) as post:
        chart_url = generator.generate_chart_url({"type": "pie", "data": []})

    assert chart_url == "https://example.com/chart.png"
    post.assert_called_once()
