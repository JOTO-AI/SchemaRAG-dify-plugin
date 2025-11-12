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
            # 验证数据不为空
            if not data:
                raise ValueError("数据列表为空")
            
            # 记录调试信息
            logger.debug(f"开始数据转换: chart_type={chart_type}, x_field={x_field}, y_field={y_field}")
            logger.debug(f"数据记录数: {len(data)}, 第一条数据: {data[0]}")
            
            if chart_type == "line":
                return DataProcessor._transform_line_data(data, x_field, y_field)
            elif chart_type == "histogram":
                return DataProcessor._transform_histogram_data(data, y_field)
            elif chart_type == "pie":
                return DataProcessor._transform_pie_data(data, x_field, y_field)
            else:
                raise ValueError(f"不支持的图表类型: {chart_type}")
                
        except KeyError as e:
            # KeyError 会返回缺失的键名
            missing_field = str(e).strip("'\"")
            available_fields = list(data[0].keys()) if data else []
            logger.error(
                f"数据转换错误: 字段'{missing_field}'不存在\n"
                f"可用字段: {available_fields}\n"
                f"数据示例: {data[0] if data else 'no data'}"
            )
            raise ValueError(
                f"数据转换错误: 字段'{missing_field}'不存在。"
                f"可用字段: {', '.join(available_fields)}"
            )
        except ValueError as e:
            if "数据转换错误" in str(e):
                # 已经是我们格式化的错误，直接抛出
                raise
            logger.error(f"数据转换错误: {str(e)}\n数据示例: {data[0] if data else 'no data'}")
            raise ValueError(f"数据转换错误: {str(e)}")
    
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
        # 先验证字段是否存在（检查第一条数据）
        if data and y_field:
            if y_field not in data[0]:
                available_fields = list(data[0].keys())
                raise KeyError(
                    f"字段 '{y_field}' 不存在。可用字段: {', '.join(available_fields)}"
                )
            if x_field not in data[0]:
                available_fields = list(data[0].keys())
                raise KeyError(
                    f"字段 '{x_field}' 不存在。可用字段: {', '.join(available_fields)}"
                )
        
        for item in data:
            # 跳过 None 值
            if y_field:
                y_value = item.get(y_field)
                x_value = item.get(x_field)
                if y_value is not None and x_value is not None:
                    result.append({
                        "time": str(x_value),
                        "value": float(str(y_value).replace(',', ''))
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
        
        # 验证字段是否存在
        if data and y_field not in data[0]:
            available_fields = list(data[0].keys())
            raise KeyError(
                f"字段 '{y_field}' 不存在。可用字段: {', '.join(available_fields)}"
            )
        
        result = []
        for item in data:
            y_value = item.get(y_field)
            if y_value is not None:
                result.append(float(str(y_value).replace(',', '')))
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
        
        # 验证字段是否存在
        if data:
            if x_field not in data[0]:
                available_fields = list(data[0].keys())
                raise KeyError(
                    f"字段 '{x_field}' 不存在。可用字段: {', '.join(available_fields)}"
                )
            if y_field and y_field not in data[0]:
                available_fields = list(data[0].keys())
                raise KeyError(
                    f"字段 '{y_field}' 不存在。可用字段: {', '.join(available_fields)}"
                )
        
        if y_field:
            # 使用 y_field 的实际值
            for item in data:
                # 跳过空的分类名称和 None 值
                x_value = item.get(x_field)
                y_value = item.get(y_field)
                if x_value and y_value is not None:
                    category = str(x_value)
                    value = float(str(y_value).replace(',', ''))
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