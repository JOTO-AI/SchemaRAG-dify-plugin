"""
LLM Plot Tool - 数据可视化工具
使用模块化架构重构
"""

from collections.abc import Generator
import json
import logging
from typing import Any

from pydantic import ValidationError

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

# 导入核心模块
from core.llm_plot import (
    ParameterValidator,
    LLMAnalyzer,
    ChartGenerator,
)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class LlmPlotTool(Tool):
    """LLM Plot 工具类"""
    
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        """
        处理插件调用请求
        
        Args:
            tool_parameters: 工具参数
            
        Yields:
            工具调用消息
        """
        try:
            # 1. 验证参数
            ParameterValidator.validate_parameters(tool_parameters)
            
            # 2. 解析参数
            user_question = tool_parameters['user_question']
            sql_query = tool_parameters['sql_query']
            data = json.loads(
                tool_parameters['data']
                if isinstance(tool_parameters['data'], str)
                else tool_parameters['data']
            )
            llm_model = tool_parameters['llm']
            
            logger.debug(f"收到参数: {json.dumps(tool_parameters, ensure_ascii=False)}")
            
            # 2.5 提取实际数据的字段列表
            data_fields = list(data[0].keys()) if data and len(data) > 0 else []
            logger.debug(f"数据字段列表: {data_fields}")
            
            # 3. 使用 LLM 分析并推荐图表
            analyzer = LLMAnalyzer(self.session)
            recommendation = analyzer.analyze(user_question, sql_query, llm_model, data_fields)
            
            logger.debug(
                f"LLM 推荐: 类型={recommendation.chart_type}, "
                f"X字段={recommendation.x_field}, "
                f"Y字段={recommendation.y_field}, "
                f"标题={recommendation.title}"
            )
            
            # 4. 生成图表
            generator = ChartGenerator()
            chart_url = generator.generate(recommendation, data)
            
            # 5. 返回结果
            result_message = f"""![生成的图表]({chart_url})"""
            yield self.create_text_message(result_message)

        except ValueError as e:
            error_msg = f"❌ 参数错误: {str(e)}"
            logger.error("参数错误 | %s | %s", str(e), type(e).__name__)
            yield self.create_text_message(error_msg)
            
        except json.JSONDecodeError as e:
            error_msg = "❌ 数据格式错误：请提供有效的JSON数据"
            logger.error(
                "JSON解析错误 | %s | %s | doc=%s", 
                str(e), 
                type(e).__name__, 
                e.doc[:200] if hasattr(e, 'doc') else 'N/A'
            )
            yield self.create_text_message(error_msg)
            
        except ValidationError as e:
            error_msg = f"❌ 参数验证错误: {str(e)}"
            logger.error("参数验证错误 | %s | %s", str(e), type(e).__name__)
            yield self.create_text_message(error_msg)
            
        except Exception as e:
            error_msg = f"❌ 图表生成失败: {str(e)}"
            logger.error(
                "未预期的错误 | %s | %s | traceback=%s",
                str(e),
                type(e).__name__,
                getattr(e, '__traceback__', 'N/A'),
                exc_info=True
            )
            yield self.create_text_message(error_msg)
