"""
图表配置 JSON 统一规范定义
这是 LLM 和 Matplotlib 模块之间沟通的桥梁
"""

from typing import Dict, List, Optional, Union, Literal
from pydantic import BaseModel, Field


class XAxisConfig(BaseModel):
    """X轴配置"""
    label: str = Field(description="X轴标签")
    data: List[Union[str, int, float]] = Field(description="X轴刻度/类别数据")


class YAxisConfig(BaseModel):
    """Y轴配置"""
    label: str = Field(description="Y轴标签")
    data: List[Union[int, float]] = Field(description="Y轴数值数据")


class PieDataConfig(BaseModel):
    """饼图数据配置"""
    labels: List[str] = Field(description="饼图标签")
    values: List[Union[int, float]] = Field(description="饼图数值")


class LineSeriesConfig(BaseModel):
    """折线图数据系列配置"""
    label: str = Field(description="数据系列标签")
    data: List[Union[int, float]] = Field(description="数据系列数值")


class ChartConfig(BaseModel):
    """图表配置主结构"""
    chart_type: Literal["bar", "line", "pie", "scatter", "histogram"] = Field(
        description="图表类型"
    )
    title: str = Field(description="图表标题")
    
    # 通用坐标轴配置（适用于柱状图、折线图、散点图等）
    x_axis: Optional[XAxisConfig] = Field(default=None, description="X轴配置")
    y_axis: Optional[YAxisConfig] = Field(default=None, description="Y轴配置")
    
    # 饼图专用配置
    pie_data: Optional[PieDataConfig] = Field(default=None, description="饼图数据配置")
    
    # 多系列折线图配置
    line_series: Optional[List[LineSeriesConfig]] = Field(
        default=None, description="多系列折线图数据"
    )
    
    # 可选样式配置
    style: Optional[Dict[str, Union[str, int, float, bool, List[Union[str, int, float]]]]] = Field(
        default=None, description="图表样式配置"
    )


# 支持的图表类型
SUPPORTED_CHART_TYPES = ["bar", "line", "pie", "scatter", "histogram"]

# JSON 规范示例
CHART_CONFIG_EXAMPLES = {
    "bar": {
        "chart_type": "bar",
        "title": "月度销售额统计",
        "x_axis": {
            "label": "月份",
            "data": ["2025-01", "2025-02", "2025-03", "2025-04"]
        },
        "y_axis": {
            "label": "销售额 (万元)",
            "data": [120, 135, 98, 156]
        }
    },
    "line": {
        "chart_type": "line",
        "title": "销售趋势分析",
        "x_axis": {
            "label": "时间",
            "data": ["2025-01", "2025-02", "2025-03", "2025-04"]
        },
        "line_series": [
            {
                "label": "产品A",
                "data": [120, 135, 98, 156]
            },
            {
                "label": "产品B", 
                "data": [89, 102, 87, 134]
            }
        ]
    },
    "pie": {
        "chart_type": "pie",
        "title": "市场份额分布",
        "pie_data": {
            "labels": ["产品A", "产品B", "产品C", "产品D"],
            "values": [35.2, 28.7, 22.1, 14.0]
        }
    }
}


def validate_chart_config(config: Dict) -> ChartConfig:
    """
    验证图表配置的有效性
    
    Args:
        config: 图表配置字典
        
    Returns:
        ChartConfig: 验证后的配置对象
        
    Raises:
        ValueError: 配置验证失败时抛出
    """
    try:
        chart_config = ChartConfig(**config)
        
        # 业务逻辑校验
        if chart_config.chart_type not in SUPPORTED_CHART_TYPES:
            raise ValueError(f"不支持的图表类型: {chart_config.chart_type}")
            
        # 根据图表类型验证必要字段
        if chart_config.chart_type in ["bar", "scatter", "histogram"]:
            if not chart_config.x_axis or not chart_config.y_axis:
                raise ValueError(f"{chart_config.chart_type}图表需要x_axis和y_axis配置")
                
        elif chart_config.chart_type == "line":
            if not chart_config.x_axis or not chart_config.line_series:
                raise ValueError("折线图需要x_axis和line_series配置")
                
        elif chart_config.chart_type == "pie":
            if not chart_config.pie_data:
                raise ValueError("饼图需要pie_data配置")
                
        return chart_config
        
    except Exception as e:
        raise ValueError(f"图表配置验证失败: {str(e)}")


def get_chart_template(chart_type: str) -> Dict:
    """
    获取指定图表类型的配置模板
    
    Args:
        chart_type: 图表类型
        
    Returns:
        Dict: 图表配置模板
    """
    if chart_type not in CHART_CONFIG_EXAMPLES:
        raise ValueError(f"不支持的图表类型: {chart_type}")
        
    return CHART_CONFIG_EXAMPLES[chart_type].copy()
