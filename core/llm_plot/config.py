"""
图表配置和模板定义

注意：AntV GPT-Vis API 仅接受以下参数：
- type: 图表类型 (必需)
- data: 数据数组 (必需)
- title: 图表标题 (可选)
- axisXTitle: X轴标题 (可选)
- axisYTitle: Y轴标题 (可选)
- theme: 主题 "default" | "dark" | "academy" (可选)
- style: 样式对象，仅支持 backgroundColor, palette, lineWidth (可选)
- binNumber: 直方图分组数量 (可选，仅直方图)

其他参数如 width, height, legend, tooltip, label, statistic 等都不被接受，
会导致 400 Bad Request 错误。

参考文档: https://github.com/antvis/GPT-Vis
"""

from typing import Dict, Any, List


class ChartConfig:
    """图表配置类"""

    # AntV API 地址
    ANTV_API_URL = "https://antv-studio.alipay.com/api/gpt-vis"

    # 基础配置模板 - 仅包含 API 接受的参数
    BASE_CONFIG: Dict[str, Any] = {
        "theme": "academy",
        "style": {
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

    # 折线图模板 - 仅包含 API 接受的参数
    LINE_CHART_TEMPLATE: Dict[str, Any] = {
        "type": "line",
        "title": "折线图",
        "axisXTitle": "X轴",
        "axisYTitle": "Y轴",
        "style": {
            "lineWidth": 3
        }
    }

    # 直方图模板 - 仅包含 API 接受的参数
    HISTOGRAM_CHART_TEMPLATE: Dict[str, Any] = {
        "type": "histogram",
        "title": "直方图",
        "binNumber": 10,
        "axisXTitle": "数值区间",
        "axisYTitle": "频数"
    }

    # 饼图模板 - 仅包含 API 接受的参数
    PIE_CHART_TEMPLATE: Dict[str, Any] = {
        "type": "pie",
        "title": "饼图"
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