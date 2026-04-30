"""
测试中文内容在图表配置中被完整保留
"""

from core.llm_plot.chart_generator import ChartGenerator
from core.llm_plot.models import ChartRecommendation


def test_chinese_line_chart_config_preserves_labels():
    """测试折线图中文标题和坐标轴数据"""
    generator = ChartGenerator()
    recommendation = ChartRecommendation(
        chart_type="line",
        title="各季度产品销量趋势",
        x_field="季度",
        y_field="销量",
        description="季度趋势适合折线图",
    )
    data = [
        {"季度": "第一季度", "销量": 150},
        {"季度": "第二季度", "销量": 180},
    ]

    config = generator.generate_chart_config(recommendation, data)

    assert config["title"] == "各季度产品销量趋势"
    assert config["axisXTitle"] == "季度"
    assert config["axisYTitle"] == "销量"
    assert config["data"][0]["time"] == "第一季度"


def test_chinese_pie_chart_config_preserves_categories():
    """测试饼图中文分类数据"""
    generator = ChartGenerator()
    recommendation = ChartRecommendation(
        chart_type="pie",
        title="市场份额分布情况",
        x_field="品牌",
        y_field="份额",
        description="份额占比适合饼图",
    )
    data = [
        {"品牌": "华为", "份额": 30},
        {"品牌": "小米", "份额": 25},
    ]

    config = generator.generate_chart_config(recommendation, data)

    assert config["title"] == "市场份额分布情况"
    assert config["data"] == [
        {"category": "华为", "value": 30},
        {"category": "小米", "value": 25},
    ]
