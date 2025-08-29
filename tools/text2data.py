from collections.abc import Generator
from typing import Any
import sys
import os
import re
from prompt import text2sql_prompt, summary_prompt
from service.knowledge_service import KnowledgeService
from service.database_service import DatabaseService
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.entities.model.message import SystemPromptMessage, UserPromptMessage
import logging

# 添加项目根目录到Python路径，以便导入service模块
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class Text2DataTool(Tool):
    """
    Text to Data Tool - Convert natural language questions to SQL queries and execute them to return data
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 初始化知识库服务
        self.api_uri = self.runtime.credentials.get("api_uri")
        self.dataset_api_key = self.runtime.credentials.get("dataset_api_key")
        self.knowledge_service = KnowledgeService(self.api_uri, self.dataset_api_key)
        self.logger = logging.getLogger(__name__)

        # 初始化数据库服务
        self.db_service = DatabaseService()

        # 从 provider 获取数据库配置
        credentials = self.runtime.credentials
        self.db_type = credentials.get("db_type")
        self.db_host = credentials.get("db_host")
        self.db_port = (
            int(credentials.get("db_port")) if credentials.get("db_port") else None
        )
        self.db_user = credentials.get("db_user")
        self.db_password = credentials.get("db_password")
        self.db_name = credentials.get("db_name")

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        """
        Convert natural language questions to SQL queries, execute them, and return formatted results
        """
        try:
            # 获取参数
            dataset_id = tool_parameters.get("dataset_id")
            llm_model = tool_parameters.get("llm")
            content = tool_parameters.get("content")
            dialect = tool_parameters.get("dialect", "mysql")
            top_k = tool_parameters.get("top_k", 5)
            retrieval_model = tool_parameters.get("retrieval_model", "semantic_search")
            output_format = tool_parameters.get("output_format", "json")

            # 验证必要参数
            if not dataset_id:
                logging.error("错误: 缺少知识库ID")
                raise ValueError("缺少知识库ID")

            if not content:
                logging.error("错误: 缺少问题内容")
                raise ValueError("缺少问题内容")

            if not llm_model:
                logging.error("错误: 缺少LLM模型配置")
                raise ValueError("缺少LLM模型配置")

            if not self.api_uri or not self.dataset_api_key:
                logging.error("错误: 缺少API配置信息")
                raise ValueError("API配置无效")

            # 验证数据库配置
            if not all(
                [
                    self.db_type,
                    self.db_host,
                    self.db_port,
                    self.db_user,
                    self.db_password,
                    self.db_name,
                ]
            ):
                logging.error("错误: 数据库配置不完整")
                raise ValueError("数据库配置无效")

            # 步骤1: 从知识库检索相关的schema信息
            logging.info("正在从知识库检索相关的数据库架构信息...")

            try:
                schema_info = self.knowledge_service.retrieve_schema_from_dataset(
                    dataset_id, content, top_k, retrieval_model
                )
            except Exception as e:
                logging.error(f"检索架构信息时发生错误: {str(e)}")
                schema_info = "未找到相关的数据库架构信息"

            if not schema_info or schema_info.strip() == "":
                logging.warning("未从知识库检索到相关的架构信息")
                schema_info = "未找到相关的数据库架构信息"

            # 步骤2: 构建预定义的prompt并生成SQL
            logging.info("正在生成SQL查询...")

            try:
                system_prompt = text2sql_prompt._build_system_prompt(
                    dialect, schema_info, content
                )

                response = self.session.model.llm.invoke(
                    model_config=llm_model,
                    prompt_messages=[
                        SystemPromptMessage(content=system_prompt),
                        UserPromptMessage(
                            content=f"请根据以下问题生成SQL查询：{content}，只要输出最终sql，避免输出任何解释或其他内容。"
                        ),
                    ],
                    stream=False,  # 不使用流式响应，确保获取完整SQL
                )

                # 提取SQL查询
                sql_query = ""
                if hasattr(response, "message") and response.message:
                    sql_query = (
                        response.message.content.strip()
                        if response.message.content
                        else ""
                    )

                if not sql_query:
                    logging.error("错误: 无法生成SQL查询")
                    raise ValueError("生成的SQL查询为空")

                # 清理SQL查询（移除markdown代码块标记等）
                sql_query = self._clean_sql_query(sql_query)

                if not sql_query or sql_query.strip() == "":
                    logging.error("错误: 生成的SQL查询为空")
                    raise ValueError("生成的SQL查询为空")

                yield self.create_text_message(
                    f"生成的SQL查询:\n```sql\n{sql_query}\n```"
                )

            except Exception as e:
                logging.error(f"生成SQL查询时发生错误: {str(e)}")
                raise

            # 步骤3: 执行SQL查询
            logging.info("正在执行SQL查询...")

            try:
                results, columns = self.db_service.execute_query(
                    self.db_type,
                    self.db_host,
                    self.db_port,
                    self.db_user,
                    self.db_password,
                    self.db_name,
                    sql_query,
                )
            except Exception as e:
                logging.error(f"执行SQL查询时发生错误: {str(e)}")
                raise

            # 步骤4: 格式化输出
            if output_format == "summary":
                # 生成数据摘要
                logging.info("正在生成数据摘要...")

                try:
                    # 先获取JSON格式的数据
                    json_data = self.db_service._format_output(results, columns, "json")

                    if not json_data or json_data.strip() == "":
                        logging.warning("警告: 查询结果为空，无法生成摘要")
                        return

                    # 使用LLM生成摘要
                    summary_system_prompt = summary_prompt._data_summary_prompt(
                        json_data, content
                    )

                    summary_response = self.session.model.llm.invoke(
                        model_config=llm_model,
                        prompt_messages=[
                            SystemPromptMessage(content=summary_system_prompt),
                            UserPromptMessage(content="请根据上述数据生成摘要。"),
                        ],
                        stream=True,
                    )

                    summary_result = ""
                    for chunk in summary_response:
                        if chunk.delta.message and chunk.delta.message.content:
                            summary_content = chunk.delta.message.content
                            summary_result += summary_content
                            yield self.create_text_message(text=summary_content)

                    # 如果没有流式响应，尝试获取完整响应
                    if (
                        not summary_result
                        and hasattr(summary_response, "message")
                        and summary_response.message
                    ):
                        summary_result = summary_response.message.content
                        if summary_result:
                            yield self.create_text_message(text=summary_result)

                except Exception as e:
                    logging.error(f"生成摘要时发生错误: {str(e)}")
                    # 如果摘要生成失败，返回原始数据
                    try:
                        formatted_output = self.db_service._format_output(
                            results, columns, "json"
                        )
                        logging.warning(
                            f"摘要生成失败，返回原始数据:\n{formatted_output}"
                        )
                    except Exception as e2:
                        logging.error(f"数据格式化也失败了: {str(e2)}")
            else:
                # 返回格式化的数据
                try:
                    formatted_output = self.db_service._format_output(
                        results, columns, output_format
                    )
                    yield self.create_text_message(text=formatted_output)
                except Exception as e:
                    logging.error(f"格式化输出时发生错误: {str(e)}")
                    raise ValueError(f"格式化输出时发生错误: {str(e)}")

        except Exception as e:
            logging.error(f"执行过程中发生错误: {str(e)}")
            raise ValueError(f"执行过程中发生错误: {str(e)}")

    def _clean_sql_query(self, sql_query: str) -> str:
        """
        清理SQL查询，移除markdown代码块标记等不必要的内容
        """
        if not sql_query:
            return ""

        # 移除markdown代码块标记
        sql_query = re.sub(r"```sql\s*", "", sql_query)
        sql_query = re.sub(r"```\s*", "", sql_query)

        # 移除前后空白
        sql_query = sql_query.strip()

        if not sql_query:
            return ""

        # 如果有多行，只取第一个完整的SQL语句
        lines = sql_query.split("\n")
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith("--") and not line.startswith("#"):
                cleaned_lines.append(line)

        # 重新组合SQL
        if cleaned_lines:
            sql_query = " ".join(cleaned_lines)
        else:
            return ""

        return sql_query.strip()
