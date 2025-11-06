"""
数据模型定义
"""

from typing import Optional
from pydantic import BaseModel, Field


class ChartRecommendation(BaseModel):
    """图表推荐模型"""
    chart_type: str = Field(..., description="图表类型：line/histogram/pie")
    x_field: str = Field(..., description="X轴字段名或分类字段")
    y_field: Optional[str] = Field(None, description="Y轴字段名或数值字段")
    title: str = Field(..., description="图表标题")
    description: str = Field(..., description="选择该图表类型的理由")

    class Config:
        json_schema_extra = {
            "example": {
                "chart_type": "line",
                "x_field": "date",
                "y_field": "sales",
                "title": "销售趋势分析",
                "description": "展示销售额随时间的变化趋势"
            }
        }