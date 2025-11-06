"""
参数验证模块
"""

import json
from typing import Any, Dict


class ParameterValidator:
    """参数验证器"""
    
    @staticmethod
    def validate_parameters(parameters: Dict[str, Any]) -> None:
        """
        验证输入参数
        
        Args:
            parameters: 需要验证的参数字典
            
        Raises:
            ValueError: 参数验证失败时抛出
        """
        # 检查必需参数
        required_params = ['user_question', 'sql_query', 'data', 'llm']
        for param in required_params:
            if param not in parameters:
                raise ValueError(f"缺少必需参数: {param}")
            if not parameters[param]:
                raise ValueError(f"参数不能为空: {param}")
        
        # 验证 data 参数格式
        ParameterValidator.validate_data_format(parameters['data'])
    
    @staticmethod
    def validate_data_format(data: Any) -> None:
        """
        验证数据格式是否为有效的 JSON
        
        Args:
            data: 需要验证的数据
            
        Raises:
            ValueError: 数据格式无效时抛出
        """
        try:
            if isinstance(data, str):
                json.loads(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"data 参数必须是有效的 JSON 格式: {str(e)}")
    
    @staticmethod
    def validate_chart_type(chart_type: str) -> None:
        """
        验证图表类型是否有效
        
        Args:
            chart_type: 图表类型
            
        Raises:
            ValueError: 图表类型无效时抛出
        """
        valid_types = ['line', 'histogram', 'pie']
        if chart_type not in valid_types:
            raise ValueError(
                f"无效的图表类型: {chart_type}. "
                f"有效类型: {', '.join(valid_types)}"
            )
    
    @staticmethod
    def validate_field_exists(data: list, field_name: str) -> None:
        """
        验证字段是否在数据中存在
        
        Args:
            data: 数据列表
            field_name: 字段名称
            
        Raises:
            ValueError: 字段不存在时抛出
        """
        if not data:
            raise ValueError("数据不能为空")
        
        if field_name and field_name not in data[0]:
            available_fields = list(data[0].keys())
            raise ValueError(
                f"字段 '{field_name}' 不存在于数据中. "
                f"可用字段: {', '.join(available_fields)}"
            )