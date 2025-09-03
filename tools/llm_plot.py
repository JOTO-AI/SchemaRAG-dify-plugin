"""
LLM 智能绘图工具 - Dify 插件版本
基于用户问题和数据，通过 LLM 智能生成图表
"""

from collections.abc import Generator
from typing import Any, Dict, Optional, Union, Tuple
import sys
import os
import json
import logging
from pathlib import Path

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.entities.model.message import SystemPromptMessage, UserPromptMessage
from dify_plugin.config.logger_format import plugin_logger_handler

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入核心模块
from core.llm_plot import (
    generate_chart,
    validate_chart_config,
    create_chart_prompt,
    SUPPORTED_CHART_TYPES
)

# 配置日志
logger = logging.getLogger(__name__)
logger.addHandler(plugin_logger_handler)

class LLMPlotTool(Tool):
    """LLM 智能绘图工具 - Dify 插件"""
    
    # 性能和配置常量
    DEFAULT_OUTPUT_DIR = "output/charts"
    MAX_CONTENT_LENGTH = 5000  # 最大输入内容长度
    MAX_DATA_SIZE = 1000000    # 最大数据大小（1MB）
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.output_dir = self.DEFAULT_OUTPUT_DIR

        self.logger = logging.getLogger(__name__)
        
        # 确保输出目录存在
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        


    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        """
        执行 LLM 智能绘图
        """

        try:
            # 验证和获取参数
            params_result = self._validate_and_extract_parameters(tool_parameters)
            if isinstance(params_result, str):  # 错误消息
                logger.error(f"错误: {params_result}")
                raise ValueError(params_result)

            user_question, data, llm_model, context = params_result

            # 步骤1: 预处理数据
            self.logger.info(f"开始处理用户问题，数据长度: {len(str(data))}")
            processed_data = self._preprocess_data(data)
            
            # 步骤2: 生成 Prompt
            prompt = create_chart_prompt(
                user_question=user_question,
                query_data=processed_data,
                additional_context=context
            )
            
            # 步骤3: 调用 LLM 生成图表配置
            self.logger.info("开始调用 LLM 生成图表配置")

            response = self.session.model.llm.invoke(
                model_config=llm_model,
                prompt_messages=[
                    SystemPromptMessage(content="你是一个专业的数据可视化专家，擅长根据用户需求和数据生成最合适的图表配置。请严格按照JSON格式返回配置，不要添加任何解释。"),
                    UserPromptMessage(content=prompt)
                ],
                stream=True,
            )

            # 收集流式响应
            llm_response = ""
            total_content_length = 0

            for chunk in response:
                if chunk.delta.message and chunk.delta.message.content:
                    content = chunk.delta.message.content
                    llm_response += content
                    total_content_length += len(content)

                    # 防止过长的响应
                    if total_content_length > 10000:  # 10KB限制
                        logger.warning("警告: LLM响应内容过长，已截断")
                        break

            if not llm_response.strip():
                logger.error("错误: LLM 未返回有效配置")
                raise ValueError("LLM 未返回有效配置")

            # 步骤4: 解析和验证配置
            chart_config = self._parse_llm_response(llm_response)
            
            # 步骤5: 生成图表
            chart_path = generate_chart(chart_config, self.output_dir)
            chart_blob = Path(chart_path).read_bytes()
            
            # 步骤6: 返回结果 - 创建blob消息并指定MIME类型
            meta = {
                "mime_type": "image/png",
                "filename": Path(chart_path).name
            }
            yield self.create_blob_message(blob=chart_blob, meta=meta)

            # 提供图表信息
            # chart_info = self._get_chart_info(chart_path)
            # if chart_info:
            #     yield self.create_text_message(chart_info)

            self.logger.info(f"图表生成完成: {chart_path}")

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析错误: {str(e)}")
            raise ValueError(f"配置解析错误: {str(e)}")
        except ValueError as e:
            self.logger.error(f"参数验证错误: {str(e)}")
            raise ValueError(f"参数错误: {str(e)}")
        except ConnectionError as e:
            self.logger.error(f"网络连接错误: {str(e)}")
            raise ValueError(f"网络连接错误: {str(e)}")
        except Exception as e:
            self.logger.error(f"图表生成异常: {str(e)}")
            raise ValueError(f"生成图表时发生错误: {str(e)}")


    def _validate_and_extract_parameters(self, tool_parameters: dict[str, Any]) -> Union[Tuple[str, Any, Any, str, bool], str]:
        """验证并提取工具参数，返回参数元组或错误消息"""
        # 验证必要参数
        user_question = tool_parameters.get("user_question")
        if not user_question or not user_question.strip():
            return "缺少用户问题描述"

        data = tool_parameters.get("data")
        if not data:
            return "缺少数据"

        llm_model = tool_parameters.get("llm")
        if not llm_model:
            return "缺少 LLM 模型配置"

        # 检查问题长度
        if len(user_question) > self.MAX_CONTENT_LENGTH:
            return f"问题描述过长，最大允许 {self.MAX_CONTENT_LENGTH} 字符，当前 {len(user_question)} 字符"

        # 检查数据大小
        if isinstance(data, str) and len(data) > self.MAX_DATA_SIZE:
            return f"数据过大，最大允许 {self.MAX_DATA_SIZE} 字符，当前 {len(data)} 字符"

        # 获取可选参数并设置默认值
        context = tool_parameters.get("context", "")


        return (user_question.strip(), data, llm_model, context)

    def _preprocess_data(self, data: Any) -> Any:
        """预处理输入数据"""
        if isinstance(data, str):
            try:
                # 尝试解析 JSON 字符串
                parsed_data = json.loads(data)
                return parsed_data
            except json.JSONDecodeError:
                # 如果不是 JSON，尝试按行分割处理CSV格式
                lines = data.strip().split('\n')
                if len(lines) > 1:
                    # 可能是 CSV 格式
                    headers = [h.strip() for h in lines[0].split(',')]
                    rows = []
                    for line in lines[1:]:
                        values = [v.strip() for v in line.split(',')]
                        if len(values) == len(headers):
                            row = {}
                            for i, header in enumerate(headers):
                                try:
                                    # 尝试转换为数字
                                    row[header] = float(values[i])
                                except ValueError:
                                    row[header] = values[i]
                            rows.append(row)
                    if rows:
                        return rows
                return data
        return data

    def _parse_llm_response(self, response: str) -> Dict:
        """解析 LLM 响应，提取 JSON 配置"""
        try:
            # 清理响应文本
            cleaned_response = self._clean_llm_response(response)
            
            # 尝试直接解析
            try:
                config = json.loads(cleaned_response)
                return config
            except json.JSONDecodeError:
                # 如果直接解析失败，尝试提取 JSON 部分
                import re
                json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
                if json_match:
                    config = json.loads(json_match.group())
                    return config
                else:
                    raise ValueError("响应中未找到有效的 JSON")
                    
        except Exception as e:
            raise ValueError(f"LLM 响应解析失败: {str(e)}")

    def _clean_llm_response(self, response: str) -> str:
        """清理 LLM 响应文本"""
        import re
        
        # 移除可能的代码块标记
        response = re.sub(r'```json\s*', '', response)
        response = re.sub(r'```\s*', '', response)
        
        # 移除多余的空白
        response = response.strip()
        
        # 移除可能的解释文字（保留 JSON 部分）
        lines = response.split('\n')
        json_start = -1
        json_end = -1
        
        for i, line in enumerate(lines):
            if line.strip().startswith('{'):
                json_start = i
                break
        
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip().endswith('}'):
                json_end = i
                break
        
        if json_start != -1 and json_end != -1:
            json_lines = lines[json_start:json_end + 1]
            response = '\n'.join(json_lines)
        
        return response

    def _get_chart_type_name(self, chart_type: str) -> str:
        """获取图表类型中文名称"""
        type_names = {
            "bar": "柱状图",
            "line": "折线图", 
            "pie": "饼图",
            "scatter": "散点图",
            "histogram": "直方图"
        }
        return type_names.get(chart_type, chart_type)

    def _get_chart_info(self, chart_path: str) -> Optional[str]:
        """获取图表信息"""
        try:
            path_obj = Path(chart_path)
            if path_obj.exists():
                size_kb = path_obj.stat().st_size / 1024
                return f"图表大小: {size_kb:.1f} KB"
        except Exception:
            pass
        return None

   