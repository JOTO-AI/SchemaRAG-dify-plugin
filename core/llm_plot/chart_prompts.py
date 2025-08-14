"""
LLM 图表生成 Prompt 模板
用于引导 LLM 生成符合规范的图表配置 JSON
"""

from typing import Dict, List, Any, Optional
import json
from .chart_schema import CHART_CONFIG_EXAMPLES, SUPPORTED_CHART_TYPES


class ChartPromptTemplate:
    """图表生成 Prompt 模板类"""
    
    def __init__(self):
        self.role_definition = """你是一位专业的数据分析师和可视化专家，擅长将复杂的数据转化为易于理解的可视化图表。你具有丰富的数据分析经验，能够根据用户的需求和数据特点选择最合适的图表类型。"""
        
        self.task_description = f"""你的任务是：
1. 仔细分析用户的原始问题和查询出的数据
2. 从以下支持的图表类型中选择最合适的一种来回答用户的问题：{SUPPORTED_CHART_TYPES}
3. 根据提供的 JSON 格式规范，提取并整理数据，生成一个完整且准确的 JSON 配置对象

图表类型选择指导：
- bar（柱状图）：适用于比较不同类别的数值，如销售额对比、人数统计等
- line（折线图）：适用于显示数据随时间的变化趋势，如销售趋势、增长率等
- pie（饼图）：适用于显示部分与整体的关系，如市场份额、比例分布等
- scatter（散点图）：适用于显示两个变量之间的相关性
- histogram（直方图）：适用于显示数据的分布情况"""
        
        self.format_requirement = """你必须严格按照以下 JSON 结构返回你的答案，不要添加任何额外的解释、代码块标记或文字。直接返回纯 JSON 格式的结果。"""
        
        self.json_schema = self._get_json_schema()
        
        self.examples = self._get_examples()
    
    def _get_json_schema(self) -> str:
        """获取 JSON 结构说明"""
        return """
JSON 结构规范：
{
  "chart_type": "string",  // 必填，图表类型: "bar", "line", "pie", "scatter", "histogram"
  "title": "string",       // 必填，图表标题，应该简洁明了地描述图表内容
  
  // 对于 bar, scatter, histogram 图表，需要以下字段：
  "x_axis": {
    "label": "string",     // x轴标签
    "data": ["array"]      // x轴数据（可以是字符串、数字）
  },
  "y_axis": {
    "label": "string",     // y轴标签  
    "data": ["array"]      // y轴数据（必须是数字）
  },
  
  // 对于 line 图表，需要以下字段：
  "x_axis": {
    "label": "string",     // x轴标签
    "data": ["array"]      // x轴数据
  },
  "line_series": [
    {
      "label": "string",   // 数据系列标签
      "data": ["array"]    // 数据系列数值（必须是数字）
    }
  ],
  
  // 对于 pie 图表，需要以下字段：
  "pie_data": {
    "labels": ["array"],   // 饼图标签（字符串数组）
    "values": ["array"]    // 饼图数值（数字数组）
  },
  
  // 可选的样式配置
  "style": {
    "figure_size": [width, height],  // 图表尺寸
    "colors": ["color1", "color2"]   // 自定义颜色
  }
}
"""
    
    def _get_examples(self) -> str:
        """获取示例说明"""
        examples_text = "配置示例：\n\n"
        for chart_type, example in CHART_CONFIG_EXAMPLES.items():
            examples_text += f"{chart_type.upper()}图示例：\n"
            examples_text += json.dumps(example, ensure_ascii=False, indent=2)
            examples_text += "\n\n"
        return examples_text
    
    def generate_prompt(self, 
                       user_question: str, 
                       query_data: Any,
                       additional_context: Optional[str] = None) -> str:
        """
        生成完整的 Prompt
        
        Args:
            user_question: 用户的原始问题
            query_data: 查询出的数据（可以是字典、列表或字符串）
            additional_context: 额外的上下文信息
            
        Returns:
            str: 完整的 Prompt 文本
        """
        # 格式化查询数据
        if isinstance(query_data, (dict, list)):
            formatted_data = json.dumps(query_data, ensure_ascii=False, indent=2)
        else:
            formatted_data = str(query_data)
        
        prompt = f"""{self.role_definition}

{self.task_description}

用户的原始问题：
{user_question}

查询出的数据：
{formatted_data}
"""
        
        if additional_context:
            prompt += f"\n额外上下文信息：\n{additional_context}\n"
        
        prompt += f"""
{self.format_requirement}

{self.json_schema}

{self.examples}

请根据以上信息，分析用户问题和数据，选择最合适的图表类型，并生成符合规范的 JSON 配置。直接返回 JSON，不要任何其他内容："""
        
        return prompt
  

def create_chart_prompt(user_question: str, 
                       query_data: Any,
                       additional_context: Optional[str] = None) -> str:
    """
    创建图表生成 Prompt 的便捷函数
    
    Args:
        user_question: 用户问题
        query_data: 查询数据
        additional_context: 额外上下文
        
    Returns:
        str: 生成的 Prompt
    """
    template = ChartPromptTemplate()
    
   
    return template.generate_prompt(user_question, query_data, additional_context)
