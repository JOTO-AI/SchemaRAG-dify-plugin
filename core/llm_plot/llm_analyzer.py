"""
LLM 分析模块
"""

import json
import logging
from typing import Any, Dict
from pydantic import ValidationError

from dify_plugin.entities.model.message import SystemPromptMessage, UserPromptMessage

from .models import ChartRecommendation

logger = logging.getLogger(__name__)


class LLMAnalyzer:
    """LLM 分析器"""
    
    # 系统提示词模板
    SYSTEM_PROMPT = """你是一位数据可视化专家。你需要分析用户问题和SQL查询，并推荐最合适的可视化方案。

你的回答必须是一个有效的JSON字符串，包含以下字段：
{
    "chart_type": "图表类型，必须是 line/histogram/pie 其中之一",
    "x_field": "X轴字段名或分类字段（必须是SQL中实际存在的字段）",
    "y_field": "Y轴字段名或数值字段（必须是SQL中实际存在的字段，饼图可选）",
    "title": "图表标题",
    "description": "选择该图表类型的理由"
}

图表选择规则：
1. 折线图(line)：适用于时间序列数据和趋势分析
2. 直方图(histogram)：适用于数值分布分析
3. 饼图(pie)：适用于占比/结构/分布数据分析

重要提示：
- 必须使用SQL查询中实际存在的字段名
- 回答必须是一个有效的JSON字符串
- 字段名称必须完全匹配上述格式"""
    
    # 默认推荐配置
    DEFAULT_RECOMMENDATION = {
        "chart_type": "pie",
        "x_field": "category",
        "y_field": "value",
        "title": "数据分布分析",
        "description": "使用饼图展示数据分布，直观显示各部分占比。"
    }
    
    def __init__(self, session):
        """
        初始化 LLM 分析器
        
        Args:
            session: Dify session 对象
        """
        self.session = session
    
    def analyze(self, user_question: str, sql_query: str, llm_model: Dict[str, Any]) -> ChartRecommendation:
        """
        使用 LLM 分析用户问题并推荐图表类型
        
        Args:
            user_question: 用户问题
            sql_query: SQL 查询语句
            llm_model: LLM 模型配置
            
        Returns:
            图表推荐结果
        """
        try:
            # 构建用户提示词
            user_prompt = self._build_user_prompt(user_question, sql_query)
            
            # 调用 LLM
            response_text = self._invoke_llm(llm_model, user_prompt)
            
            # 解析响应
            return self._parse_response(response_text)
            
        except Exception as e:
            logger.error(f"LLM 分析失败: {str(e)}")
            return self._get_default_recommendation()
    
    def _build_user_prompt(self, user_question: str, sql_query: str) -> str:
        """
        构建用户提示词
        
        Args:
            user_question: 用户问题
            sql_query: SQL 查询
            
        Returns:
            完整的用户提示词
        """
        return f"""请分析以下用户问题和SQL查询，推荐最合适的可视化方案：

用户问题: {user_question}
SQL查询: {sql_query}

请确保使用SQL中实际存在的字段名，并以JSON格式回答。"""
    
    def _invoke_llm(self, llm_model: Dict[str, Any], user_prompt: str) -> str:
        """
        调用 LLM 获取响应
        
        Args:
            llm_model: LLM 模型配置
            user_prompt: 用户提示词
            
        Returns:
            LLM 响应文本
        """
        response_generator = self.session.model.llm.invoke(
            model_config=llm_model,
            prompt_messages=[
                SystemPromptMessage(content=self.SYSTEM_PROMPT),
                UserPromptMessage(content=user_prompt),
            ],
            stream=False
        )
        
        # 收集完整响应
        response_text = ""
        for key, value in response_generator:
            if key == 'message' and hasattr(value, 'content'):
                response_text = value.content
                break
        
        logger.debug(f"LLM 完整响应: {response_text}")
        return response_text
    
    def _parse_response(self, response_text: str) -> ChartRecommendation:
        """
        解析 LLM 响应
        
        Args:
            response_text: LLM 响应文本
            
        Returns:
            图表推荐结果
        """
        try:
            recommendation = json.loads(response_text)
            return ChartRecommendation(**recommendation)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"LLM 响应解析失败: {str(e)}\nLLM 响应: {response_text}")
            return self._get_default_recommendation()
    
    def _get_default_recommendation(self) -> ChartRecommendation:
        """
        获取默认推荐配置
        
        Returns:
            默认的图表推荐
        """
        return ChartRecommendation(**self.DEFAULT_RECOMMENDATION)
    
    @classmethod
    def create_recommendation(
        cls,
        chart_type: str,
        x_field: str,
        y_field: str = None,
        title: str = "",
        description: str = ""
    ) -> ChartRecommendation:
        """
        创建图表推荐
        
        Args:
            chart_type: 图表类型
            x_field: X轴字段
            y_field: Y轴字段
            title: 标题
            description: 描述
            
        Returns:
            图表推荐对象
        """
        return ChartRecommendation(
            chart_type=chart_type,
            x_field=x_field,
            y_field=y_field,
            title=title or f"{chart_type.capitalize()} Chart",
            description=description or f"Visualization using {chart_type} chart"
        )