"""
图表配置和模板定义
"""

from typing import Dict, Any, List


class ChartConfig:
    """图表配置类"""
    
    # AntV API 地址
    ANTV_API_URL = "https://antv-studio.alipay.com/api/gpt-vis"
    
    # 基础配置模板
    BASE_CONFIG: Dict[str, Any] = {
        "source": "dify-plugin-visualization",
        "theme": "academy",
        "width": 800,
        "height": 600,
        "style": {
            "texture": "default",
            "backgroundColor": "#ffffff",
            "palette": [
                "#5B8FF9",  # 蓝色
                "#61DDAA",  # 绿色
                "#F6BD16",  # 黄色
                "#7262fd",  # 紫色
                "#78D3F8",  # 青色
                "#9661BC",  # 深紫色
                "#F6903D",  # 橙色
                "#008685",  # 青绿色
                "#F08BB4",  # 粉色
            ]
        }
    }
    
    # 折线图模板
    LINE_CHART_TEMPLATE: Dict[str, Any] = {
        "type": "line",
        "title": "折线图",
        "axisXTitle": "X轴",
        "axisYTitle": "Y轴",
        "style": {
            "lineWidth": 3,
            "smooth": True,
        },
        "stack": False,
        "legend": {
            "position": "top-right"
        },
        "tooltip": {
            "showTitle": True,
            "showMarkers": True
        }
    }
    
    # 直方图模板
    HISTOGRAM_CHART_TEMPLATE: Dict[str, Any] = {
        "type": "histogram",
        "title": "直方图",
        "binNumber": 10,
        "axisXTitle": "数值区间",
        "axisYTitle": "频数",
        "style": {
            "backgroundColor": "#f6f8fa",
            "fillOpacity": 0.8
        },
        "tooltip": {
            "showTitle": True
        }
    }
    
    # 饼图模板
    PIE_CHART_TEMPLATE: Dict[str, Any] = {
        "type": "pie",
        "title": "饼图",
        "innerRadius": 0.5,  # 环形图
        "width": 800,
        "height": 600,
        "legend": {
            "position": "right"
        },
        "label": {
            "type": "inner",
            "offset": "-30%",
            "style": {
                "fontSize": 14,
                "textAlign": "center"
            }
        },
        "tooltip": {
            "showTitle": False
        },
        "statistic": {
            "title": {
                "offsetY": -8,
                "style": {
                    "fontSize": "14px"
                }
            },
            "content": {
                "offsetY": 4,
                "style": {
                    "fontSize": "20px"
                }
            }
        }
    }
    
    @classmethod
    def get_chart_template(cls, chart_type: str) -> Dict[str, Any]:
        """
        获取指定类型的图表模板
        
        Args:
            chart_type: 图表类型 (line/histogram/pie)
            
        Returns:
            图表模板配置
        """
        templates = {
            "line": cls.LINE_CHART_TEMPLATE,
            "histogram": cls.HISTOGRAM_CHART_TEMPLATE,
            "pie": cls.PIE_CHART_TEMPLATE,
        }
        return templates.get(chart_type, cls.PIE_CHART_TEMPLATE).copy()
    
    @classmethod
    def merge_config(cls, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并配置，深度合并字典
        
        Args:
            base: 基础配置
            override: 覆盖配置
            
        Returns:
            合并后的配置
        """
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = cls.merge_config(result[key], value)
            else:
                result[key] = value
        return result
    
    @classmethod
    def create_chart_config(
        cls,
        chart_type: str,
        data: List[Any],
        title: str = "",
        x_title: str = "",
        y_title: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """
        创建完整的图表配置
        
        Args:
            chart_type: 图表类型
            data: 图表数据
            title: 图表标题
            x_title: X轴标题
            y_title: Y轴标题
            **kwargs: 其他配置参数
            
        Returns:
            完整的图表配置
        """
        # 获取基础配置和模板
        config = cls.merge_config(cls.BASE_CONFIG, cls.get_chart_template(chart_type))
        
        # 设置数据和标题
        config["data"] = data
        if title:
            config["title"] = title
        if x_title and "axisXTitle" in config:
            config["axisXTitle"] = x_title
        if y_title and "axisYTitle" in config:
            config["axisYTitle"] = y_title
        
        # 合并额外配置
        if kwargs:
            config = cls.merge_config(config, kwargs)
        
        return config