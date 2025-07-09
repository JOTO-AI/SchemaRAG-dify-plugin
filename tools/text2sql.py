from collections.abc import Generator
from typing import Any
import sys
import os

# 添加项目根目录到Python路径，以便导入service模块
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from prompt import text2sql_prompt
from service.knowledge_service import KnowledgeService

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.entities.model.message import SystemPromptMessage, UserPromptMessage


class Text2SQLTool(Tool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_uri = self.runtime.credentials.get("api_uri")
        self.dataset_api_key = self.runtime.credentials.get("dataset_api_key")
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
            # yield self.create_text_message(f"正在从知识库 {dataset_id} 检索相关的数据库架构信息...")

            schema_info = self.knowledge_service.retrieve_schema_from_dataset(
                dataset_id, content, top_k, retrieval_model
            )

            # if not schema_info:
            #     yield self.create_text_message("警告: 未从知识库检索到相关的架构信息")
            #     schema_info = "未找到相关的数据库架构信息"
            # else:
            #     yield self.create_text_message(f"检索到相关架构信息，开始生成SQL...")

            # 步骤2: 构建预定义的prompt
            system_prompt = text2sql_prompt._build_system_prompt(dialect, schema_info, content)

            # 步骤3: 调用LLM生成SQL
            # yield self.create_text_message("正在生成SQL查询...")

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
                    yield self.create_text_message(text=sql_content)

            # 如果没有流式响应，尝试获取完整响应
            if not sql_result and hasattr(response, "message") and response.message:
                sql_result = response.message.content
                yield self.create_text_message(text=sql_result)

        except Exception as e:
            yield self.create_text_message(f"生成SQL时发生错误: {str(e)}")

