"""
LLM 分析模块
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from dify_plugin.entities.model.message import SystemPromptMessage, UserPromptMessage

from .models import ChartRecommendation

logger = logging.getLogger(__name__)


class LLMAnalyzer:
    """LLM 分析器"""

    # 系统提示词模板
    SYSTEM_PROMPT = """你是一位数据可视化专家。你需要分析用户问题和SQL查询，并推荐最合适的可视化方案。

你的回答必须是一个有效的JSON字符串（不要使用markdown代码块），包含以下字段：
{
    "chart_type": "图表类型，必须是 line/histogram/pie 其中之一",
    "x_field": "X轴字段名或分类字段",
    "y_field": "Y轴字段名或数值字段（饼图可选）",
    "title": "图表标题",
    "description": "选择该图表类型的理由"
}

图表选择规则：
1. 折线图(line)：适用于时间序列数据和趋势分析
2. 直方图(histogram)：适用于数值分布分析
3. 饼图(pie)：适用于占比/结构/分布数据分析

⚠️ 极其重要的规则：
- x_field 和 y_field 必须使用用户提供的"可用的数据字段"列表中的字段名
- 字段名必须完全匹配，包括中文字符、大小写等
- 不能使用通用的英文字段名（如 category、value、sales 等）
- 必须使用实际数据中存在的字段名
- 直接返回JSON字符串，不要使用```json```代码块包裹"""
    
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
    
    def analyze(
        self,
        user_question: str,
        sql_query: str,
        llm_model: Dict[str, Any],
        data_fields: Optional[List[str]] = None
    ) -> ChartRecommendation:
        """
        使用 LLM 分析用户问题并推荐图表类型

        Args:
            user_question: 用户问题
            sql_query: SQL 查询语句
            llm_model: LLM 模型配置
            data_fields: 实际数据的字段列表

        Returns:
            图表推荐结果
        """
        try:
            # 构建用户提示词
            user_prompt = self._build_user_prompt(user_question, sql_query, data_fields)

            # 调用 LLM
            response_text = self._invoke_llm(llm_model, user_prompt)

            # 解析响应
            return self._parse_response(response_text, data_fields)

        except Exception as e:
            logger.error(f"LLM 分析失败: {str(e)}")
            return self._get_default_recommendation(data_fields)
    
    def _build_user_prompt(self, user_question: str, sql_query: str, data_fields: list = None) -> str:
        """
        构建用户提示词
        
        Args:
            user_question: 用户问题
            sql_query: SQL 查询
            data_fields: 实际数据的字段列表
            
        Returns:
            完整的用户提示词
        """
        fields_info = ""
        if data_fields:
            fields_info = f"\n可用的数据字段: {', '.join(data_fields)}"
        
        return f"""请分析以下用户问题和SQL查询，推荐最合适的可视化方案：

用户问题: {user_question}
SQL查询: {sql_query}{fields_info}

重要提示：x_field 和 y_field 必须从上面列出的可用字段中选择，不能使用其他字段名。
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
    
    def _extract_json_from_response(self, response_text: str) -> str:
        """
        从 LLM 响应中提取 JSON 字符串，处理 markdown 代码块包裹的情况

        Args:
            response_text: LLM 响应文本

        Returns:
            提取的 JSON 字符串
        """
        if not response_text:
            return response_text

        # 去除首尾空白
        text = response_text.strip()

        # 尝试匹配 ```json ... ``` 或 ``` ... ``` 代码块
        code_block_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
        match = re.search(code_block_pattern, text)
        if match:
            return match.group(1).strip()

        # 尝试匹配 { ... } JSON 对象
        json_pattern = r'\{[\s\S]*\}'
        match = re.search(json_pattern, text)
        if match:
            return match.group(0)

        return text

    def _parse_response(
        self,
        response_text: str,
        data_fields: Optional[List[str]] = None
    ) -> ChartRecommendation:
        """
        解析 LLM 响应

        Args:
            response_text: LLM 响应文本
            data_fields: 实际数据的字段列表

        Returns:
            图表推荐结果
        """
        try:
            # 提取 JSON 字符串（处理 markdown 代码块）
            json_text = self._extract_json_from_response(response_text)
            recommendation = json.loads(json_text)
            return ChartRecommendation(**recommendation)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(f"LLM 响应解析失败: {str(e)}\nLLM 响应: {response_text}")
            return self._get_default_recommendation(data_fields)

    def _get_default_recommendation(
        self,
        data_fields: Optional[List[str]] = None
    ) -> ChartRecommendation:
        """
        获取默认推荐配置，使用实际数据字段

        Args:
            data_fields: 实际数据的字段列表

        Returns:
            默认的图表推荐
        """
        # 如果有实际数据字段，使用第一个作为 x_field，第二个作为 y_field
        if data_fields and len(data_fields) >= 2:
            return ChartRecommendation(
                chart_type="line",
                x_field=data_fields[0],
                y_field=data_fields[1],
                title="数据趋势分析",
                description="使用折线图展示数据趋势变化。"
            )
        elif data_fields and len(data_fields) == 1:
            return ChartRecommendation(
                chart_type="pie",
                x_field=data_fields[0],
                y_field=None,
                title="数据分布分析",
                description="使用饼图展示数据分布。"
            )
        else:
            # 没有字段信息时使用原默认值
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