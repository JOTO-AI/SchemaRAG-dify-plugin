"""
LLM 智能绘图模块
提供基于 LLM 的智能图表生成功能
"""

from .chart_schema import (
    ChartConfig,
    XAxisConfig,
    YAxisConfig,
    PieDataConfig,
    LineSeriesConfig,
    SUPPORTED_CHART_TYPES,
    CHART_CONFIG_EXAMPLES,
    validate_chart_config,
    get_chart_template
)

from .chart_generator import (
    ChartGenerator,
    generate_chart
)

from .chart_prompts import (
    ChartPromptTemplate,
    create_chart_prompt
)

from .chart_controller import (
    LLMChartController,
    LLMChartService,
    chart_service,
    initialize_chart_service,
    generate_smart_chart
)

__version__ = "1.0.0"

__all__ = [
    # 核心类
    "ChartConfig",
    "ChartGenerator", 
    "LLMChartController",
    "LLMChartService",
    
    # 配置相关
    "XAxisConfig",
    "YAxisConfig", 
    "PieDataConfig",
    "LineSeriesConfig",
    "SUPPORTED_CHART_TYPES",
    "CHART_CONFIG_EXAMPLES",
    
    # 验证和模板
    "validate_chart_config",
    "get_chart_template",
    
    # Prompt 相关
    "ChartPromptTemplate",
    "create_chart_prompt",
    
    # 服务和便捷函数
    "chart_service",
    "initialize_chart_service", 
    "generate_smart_chart",
    "generate_chart"
]
