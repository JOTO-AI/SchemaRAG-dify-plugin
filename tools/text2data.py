from collections.abc import Generator
from typing import Any, Dict, List
import json
import pandas as pd
import requests
import sys
import os

# 添加项目根目录到Python路径，以便导入service模块
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from prompt import text2sql_prompt, summary_prompt

from service.database_service import DatabaseService
from service.knowledge_service import KnowledgeService

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.entities.model.message import SystemPromptMessage, UserPromptMessage


class Text2DataTool(Tool):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        credentials = self.runtime.credentials
        self.db_type = credentials.get("db_type")
        self.db_host = credentials.get("db_host")
        self.db_port = int(credentials.get("db_port"))
        self.db_user = credentials.get("db_user")
        self.db_password = credentials.get("db_password")
        self.db_name = credentials.get("db_name")
        self.api_uri = credentials.get("api_uri")
        self.dataset_api_key = credentials.get("dataset_api_key")
        # 初始化数据库服务
        self.db_service = DatabaseService()
        # 创建知识库服务实例
        self.knowledge_service = KnowledgeService(self.api_uri, self.dataset_api_key)

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        """
        Convert natural language questions to SQL queries using database schema knowledge base
        """
        try:
            # 获取参数
            dataset_id = tool_parameters.get("dataset_id")
            llm_model = tool_parameters.get("llm")
            content = tool_parameters.get("content")
            dialect = tool_parameters.get("dialect", "mysql")
            top_k = tool_parameters.get("top_k", 5)
            retrieval_model = tool_parameters.get("retrieval_model", "semantic_search")
            output_format = tool_parameters.get("output_format", "summary")

            # 验证必要参数
            if not dataset_id:
                yield self.create_text_message("错误: 缺少知识库ID")
                return

            if not content:
                yield self.create_text_message("错误: 缺少问题内容")
                return

            if not llm_model:
                yield self.create_text_message("错误: 缺少LLM模型配置")
                return

            if not self.api_uri or not self.dataset_api_key:
                yield self.create_text_message("错误: 缺少API配置信息")
                return

            # 步骤1: 从知识库检索相关的schema信息
            schema_info = self.knowledge_service.retrieve_schema_from_dataset(
                dataset_id, content, top_k, retrieval_model
            )

            # 步骤2: 构建预定义的prompt
            system_prompt = text2sql_prompt._build_system_prompt(dialect, schema_info, content)

            # 步骤3: 调用LLM生成SQL
            response = self.session.model.llm.invoke(
                model_config=llm_model,
                prompt_messages=[
                    SystemPromptMessage(content=system_prompt),
                    UserPromptMessage(
                        content=f"请根据以下问题生成SQL查询：{content}，只要输出最终sql，避免输出任何解释或其他内容。"
                    ),
                ],
                stream=True,
            )

            sql_result = ""
            for chunk in response:
                if chunk.delta.message and chunk.delta.message.content:
                    sql_content = chunk.delta.message.content
                    sql_result += sql_content

            # 如果没有流式响应，尝试获取完整响应
            if not sql_result and hasattr(response, "message") and response.message:
                sql_result = response.message.content

            # 步骤4: 执行查询
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
                yield self.create_text_message(
                    "Error: Database configuration is incomplete in the provider."
                )
                return

            try:
                results, columns = self.db_service.execute_query(
                    self.db_type,
                    self.db_host,
                    self.db_port,
                    self.db_user,
                    self.db_password,
                    self.db_name,
                    sql_result,
                )
            except Exception as e:
                yield self.create_text_message(
                    f"Error: Failed to execute query - {str(e)}"
                )
                return

            results, columns = self.db_service.execute_query(
                self.db_type,
                self.db_host,
                self.db_port,
                self.db_user,
                self.db_password,
                self.db_name,
                sql_result,
            )

            # 步骤5: 根据输出格式返回结果
            if output_format == "summary":
                yield from self._invoke_data_summary(results, content, llm_model)
            else:
                formatted_output = self.db_service._format_output(results, columns, output_format)
                yield self.create_text_message(text=formatted_output)

        except Exception as e:
            yield self.create_text_message(f"生成SQL时发生错误: {str(e)}")

    def _invoke_data_summary(
        self, data, query, llm_model
    ) -> Generator[ToolInvokeMessage, None, str]:
        """
        Invoke data summary with streaming response

        Args:
            data: The data to summarize
            query: The original user query content
            llm_model: The LLM model to use

        Yields:
            ToolInvokeMessage: Streaming text messages

        Returns:
            str: The complete summary result
        """
        # Convert data to JSON string
        data_content = json.dumps(data, ensure_ascii=False, indent=2)
        data_summary_prompt = summary_prompt._data_summary_prompt(data_content, query)

        # Invoke LLM for summarization
        summary_response = self.session.model.llm.invoke(
            model_config=llm_model,
            prompt_messages=[
                SystemPromptMessage(content="You are a data summarization expert."),
                UserPromptMessage(content=data_summary_prompt),
            ],
            stream=True,
        )

        # Process streaming response
        summary_result = ""
        buffer = ""  # Buffer for collecting chunks into meaningful segments

        for chunk in summary_response:
            if chunk.delta.message and chunk.delta.message.content:
                content = chunk.delta.message.content
                summary_result += content
                buffer += content

                # Send response when buffer contains complete words/sentences
                if buffer.endswith((".", "!", "?", "\n")) or len(buffer) > 80:
                    yield self.create_text_message(text=buffer)
                    buffer = ""

        # Send any remaining content in buffer
        if buffer:
            yield self.create_text_message(text=buffer)

        return summary_result

    


