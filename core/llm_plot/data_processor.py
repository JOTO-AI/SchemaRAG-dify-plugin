"""
数据处理模块
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DataProcessor:
    """数据处理器"""
    
    @staticmethod
    def transform_data_for_chart(
        chart_type: str,
        data: List[Dict],
        x_field: str,
        y_field: Optional[str] = None
    ) -> List[Any]:
        """
        转换数据为图表所需格式
        
        Args:
            chart_type: 图表类型 (line/histogram/pie)
            data: 原始数据列表
            x_field: X轴字段名
            y_field: Y轴字段名（可选）
            
        Returns:
            转换后的图表数据
            
        Raises:
            ValueError: 数据转换失败时抛出
        """
        try:
            if chart_type == "line":
                return DataProcessor._transform_line_data(data, x_field, y_field)
            elif chart_type == "histogram":
                return DataProcessor._transform_histogram_data(data, y_field)
            elif chart_type == "pie":
                return DataProcessor._transform_pie_data(data, x_field, y_field)
            else:
                raise ValueError(f"不支持的图表类型: {chart_type}")
                
        except (KeyError, ValueError) as e:
            logger.error(f"数据转换错误: {str(e)}\n数据示例: {data[0] if data else 'no data'}")
            field_name = x_field if 'x_field' in str(e) else y_field
            raise ValueError(f"数据转换错误: 字段'{field_name}'不存在或格式错误")
    
    @staticmethod
    def _transform_line_data(
        data: List[Dict],
        x_field: str,
        y_field: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        转换折线图数据
        
        Args:
            data: 原始数据
            x_field: X轴字段
            y_field: Y轴字段
            
        Returns:
            折线图数据格式: [{"time": "...", "value": ...}, ...]
        """
        result = []
        for item in data:
            # 跳过 None 值
            if y_field and item.get(y_field) is not None:
                result.append({
                    "time": str(item[x_field]),
                    "value": float(str(item[y_field]).replace(',', ''))
                })
        return result
    
    @staticmethod
    def _transform_histogram_data(
        data: List[Dict],
        y_field: Optional[str]
    ) -> List[float]:
        """
        转换直方图数据
        
        Args:
            data: 原始数据
            y_field: 数值字段
            
        Returns:
            直方图数据格式: [value1, value2, ...]
        """
        if not y_field:
            return []
        
        result = []
        for item in data:
            if item.get(y_field) is not None:
                result.append(float(str(item[y_field]).replace(',', '')))
        return result
    
    @staticmethod
    def _transform_pie_data(
        data: List[Dict],
        x_field: str,
        y_field: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        转换饼图数据
        
        Args:
            data: 原始数据
            x_field: 分类字段
            y_field: 数值字段（可选）
            
        Returns:
            饼图数据格式: [{"category": "...", "value": ...}, ...]
        """
        result = []
        
        if y_field:
            # 使用 y_field 的实际值
            for item in data:
                # 跳过空的分类名称和 None 值
                if item.get(x_field) and item.get(y_field) is not None:
                    category = str(item[x_field])
                    value = float(str(item[y_field]).replace(',', ''))
                    result.append({
                        "category": category,
                        "value": value
                    })
        else:
            # 如果没有 y_field，统计每个类别的数量
            category_count = {}
            for item in data:
                if item.get(x_field):  # 跳过空的分类名称
                    category = str(item[x_field])
                    category_count[category] = category_count.get(category, 0) + 1
            
            # 转换为饼图数据格式
            for category, count in category_count.items():
                result.append({
                    "category": category,
                    "value": count
                })
        
        return result
    
    @staticmethod
    def clean_data(data: List[Dict]) -> List[Dict]:
        """
        清洗数据，移除无效记录
        
        Args:
            data: 原始数据列表
            
        Returns:
            清洗后的数据列表
        """
        cleaned = []
        for item in data:
            if item and any(v is not None for v in item.values()):
                cleaned.append(item)
        return cleaned
    
    @staticmethod
    def get_data_summary(data: List[Dict]) -> Dict[str, Any]:
        """
        获取数据摘要信息
        
        Args:
            data: 数据列表
            
        Returns:
            数据摘要，包含记录数、字段列表等
        """
        if not data:
            return {
                "record_count": 0,
                "fields": [],
                "sample": None
            }
        
        return {
            "record_count": len(data),
            "fields": list(data[0].keys()) if data else [],
            "sample": data[0] if data else None
        }