from collections.abc import Generator
from typing import Any, Optional
import sys
import os
import json
import logging
from prompt.summary_prompt import _data_summary_prompt
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.entities.model.message import SystemPromptMessage, UserPromptMessage

# 添加项目根目录到Python路径，以便导入service模块
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class DataSummaryTool(Tool):
    """
    Data Summary Tool - Analyze and summarize data content using LLM with optional custom rules
    """

    # 配置常量
    MAX_DATA_LENGTH = 50000  # 最大数据内容长度
    MAX_RULES_LENGTH = 2000  # 最大自定义规则长度

    # 已移除分析类型和输出结构相关常量

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger(__name__)

    def _validate_input_data(
        self, data_content: str, query: str, custom_rules: Optional[str] = None
    ) -> tuple[bool, str]:
        """
        验证输入数据的有效性
        """
        if not data_content or not data_content.strip():
            return False, "数据内容不能为空"

        if not query or not query.strip():
            return False, "分析查询不能为空"

        if len(data_content) > self.MAX_DATA_LENGTH:
            return False, f"数据内容过长，最大支持 {self.MAX_DATA_LENGTH} 字符"

        if custom_rules and len(custom_rules) > self.MAX_RULES_LENGTH:
            return False, f"自定义规则过长，最大支持 {self.MAX_RULES_LENGTH} 字符"

        return True, ""

    def _format_data_content(self, data_content: str, data_format: str = "auto") -> str:
        """
        格式化数据内容，尝试解析不同的数据格式 - 优化版本
        """
        # 快速检查是否需要JSON格式化
        if data_format == "json" or (
            data_format == "auto" and data_content.lstrip().startswith(("{", "["))
        ):
            try:
                parsed_data = json.loads(data_content)
                return json.dumps(parsed_data, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                pass

        # 返回去除首尾空白的原始内容
        return data_content.strip()

    def _truncate_data_if_needed(
        self, data_content: str, max_length: int = None
    ) -> tuple[str, bool]:
        """
        如果数据过长则截断，返回截断后的数据和是否被截断的标志
        """
        if max_length is None:
            max_length = self.MAX_DATA_LENGTH

        if len(data_content) <= max_length:
            return data_content, False

        # 截断数据并添加提示
        truncated_data = data_content[: max_length - 100]  # 预留空间给提示信息
        truncated_data += "\n\n[注意: 数据内容过长已被截断，以上为部分数据内容]"

        return truncated_data, True

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        """
        执行数据摘要分析（已移除分析类型和输出结构参数，支持自定义prompt）
        """
        try:
            # 获取参数
            data_content = tool_parameters.get("data_content", "")
            query = tool_parameters.get("query", "")
            llm_model = tool_parameters.get("llm")
            custom_rules = tool_parameters.get("custom_rules", "")
            user_prompt = tool_parameters.get(
                "user_prompt", ""
            )  # 新增：支持用户自定义prompt
            data_format = "auto"

            # 验证必要参数
            if not llm_model:
                self.logger.error("错误: 缺少LLM模型配置")
                raise ValueError("缺少LLM模型配置")

            is_valid, error_message = self._validate_input_data(
                data_content, query, custom_rules
            )
            if not is_valid:
                self.logger.error(f"输入验证失败: {error_message}")
                raise ValueError(error_message)

            # 格式化数据内容
            try:
                formatted_data = self._format_data_content(data_content, data_format)
                self.logger.info("数据格式化完成")
            except Exception as e:
                self.logger.warning(f"数据格式化失败，使用原始格式: {str(e)}")
                formatted_data = data_content

            # 检查并截断过长的数据
            final_data, was_truncated = self._truncate_data_if_needed(formatted_data)
            if was_truncated:
                self.logger.info("注意: 数据内容过长，已自动截断部分内容进行分析")

            # 构建prompt逻辑
            if user_prompt and user_prompt.strip():
                # 用户自定义prompt优先
                system_prompt_content = "你是一个专业的数据分析专家，请根据用户自定义的分析指令和数据进行分析。"
                user_prompt_content = user_prompt.replace(
                    "{{data}}", final_data
                ).replace("{{query}}", query)
                self.logger.info("使用用户自定义prompt")
            elif custom_rules and custom_rules.strip():
                # 有自定义规则
                analysis_prompt = _data_summary_prompt(final_data, query, custom_rules)
                system_prompt_content = (
                    "你是一个专业的数据分析专家，请根据提供的规则和数据进行深入分析。"
                )
                user_prompt_content = analysis_prompt
                self.logger.info("使用自定义规则构建分析prompt")
            else:
                # 默认prompt
                analysis_prompt = _data_summary_prompt(final_data, query)
                system_prompt_content = (
                    "你是一个专业的数据分析专家，请根据数据和问题进行分析。"
                )
                user_prompt_content = analysis_prompt
                self.logger.info("使用默认分析prompt")

            self.logger.info("正在调用大语言模型进行数据分析...")

            try:
                response = self.session.model.llm.invoke(
                    model_config=llm_model,
                    prompt_messages=[
                        SystemPromptMessage(content=system_prompt_content),
                        UserPromptMessage(content=user_prompt_content),
                    ],
                    stream=True,
                )
                has_streamed_content = False
                total_content_length = 0

                for chunk in response:
                    if chunk.delta.message and chunk.delta.message.content:
                        content = chunk.delta.message.content
                        has_streamed_content = True
                        total_content_length += len(content)
                        if total_content_length > 50000:
                            yield self.create_text_message("警告: 响应内容过长，已截断")
                            break
                        yield self.create_text_message(text=content)

                if (
                    not has_streamed_content
                    and hasattr(response, "message")
                    and response.message
                ):
                    yield self.create_text_message(text=response.message.content)

                self.logger.info(f"数据分析完成，响应长度: {total_content_length}")

            except Exception as e:
                error_msg = f"调用LLM时发生错误: {str(e)}"
                self.logger.error(error_msg)
                raise ValueError(error_msg)

        except Exception as e:
            error_msg = f"数据摘要工具执行失败: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg)
