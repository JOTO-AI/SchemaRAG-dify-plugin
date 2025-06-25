from collections.abc import Generator
from typing import Any
import json
import requests

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.entities.model.message import SystemPromptMessage, UserPromptMessage


class Text2SQLTool(Tool):
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

            # 获取配置信息
            api_uri = self.runtime.credentials.get("api_uri")
            dataset_api_key = self.runtime.credentials.get("dataset_api_key")

            if not api_uri or not dataset_api_key:
                yield self.create_text_message("错误: 缺少API配置信息")
                return

            # 步骤1: 从知识库检索相关的schema信息
            # yield self.create_text_message(f"正在从知识库 {dataset_id} 检索相关的数据库架构信息...")

            schema_info = self._retrieve_schema_from_dataset(
                api_uri, dataset_api_key, dataset_id, content, top_k, retrieval_model
            )

            # if not schema_info:
            #     yield self.create_text_message("警告: 未从知识库检索到相关的架构信息")
            #     schema_info = "未找到相关的数据库架构信息"
            # else:
            #     yield self.create_text_message(f"检索到相关架构信息，开始生成SQL...")

            # 步骤2: 构建预定义的prompt
            system_prompt = self._build_system_prompt(dialect, schema_info, content)

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

    def _retrieve_schema_from_dataset(
        self,
        api_uri: str,
        api_key: str,
        dataset_id: str,
        query: str,
        top_k: int,
        retrieval_model: str,
    ) -> str:
        """
        从Dify知识库检索相关的schema信息
        """
        try:
            # 构建检索API URL
            url = f"{api_uri.rstrip('/')}/datasets/{dataset_id}/retrieve"

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            # 构建请求体
            data = {
                "query": query,
                "retrieval_model": {
                    "search_method": retrieval_model,
                    "reranking_enable": False,
                    "reranking_model": {
                        "reranking_provider_name": "",
                        "reranking_model_name": "",
                    },
                    "top_k": top_k,
                    "score_threshold_enabled": False,
                },
            }

            response = requests.post(url, headers=headers, json=data, timeout=30)

            if response.status_code == 200:
                result = response.json()

                # 提取检索到的内容
                schema_contents = []
                if "records" in result:
                    for record in result["records"]:
                        if "segment" in record and "content" in record["segment"]:
                            schema_contents.append(record["segment"]["content"])

                return "\n\n".join(schema_contents)
            else:
                # 如果检索API失败，尝试使用文档片段API作为备选
                return self._fallback_retrieve_documents(api_uri, api_key, dataset_id)

        except Exception as e:
            # 如果出错，尝试备选方法
            return self._fallback_retrieve_documents(api_uri, api_key, dataset_id)

    def _fallback_retrieve_documents(
        self, api_uri: str, api_key: str, dataset_id: str
    ) -> str:
        """
        备选方法：获取数据集中的文档信息
        """
        try:
            # 首先获取数据集中的文档列表
            url = f"{api_uri.rstrip('/')}/datasets/{dataset_id}/documents"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                documents = response.json()
                schema_contents = []

                # 获取前几个文档的片段
                if "data" in documents:
                    for doc in documents["data"][:3]:  # 限制获取前3个文档
                        doc_id = doc.get("id")
                        if doc_id:
                            segments = self._get_document_segments(
                                api_uri, api_key, dataset_id, doc_id
                            )
                            if segments:
                                schema_contents.extend(segments)

                return "\\n\\n".join(schema_contents)

            return ""

        except Exception:
            return ""

    def _get_document_segments(
        self, api_uri: str, api_key: str, dataset_id: str, document_id: str
    ) -> list:
        """
        获取文档的片段内容
        """
        try:
            url = f"{api_uri.rstrip('/')}/datasets/{dataset_id}/documents/{document_id}/segments"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                result = response.json()
                segments = []

                if "data" in result:
                    for segment in result["data"][:5]:  # 限制每个文档最多5个片段
                        if "content" in segment and segment["content"]:
                            segments.append(segment["content"])

                return segments

            return []

        except Exception:
            return []

    def _build_system_prompt(self, dialect: str, db_schema: str, question: str) -> str:
        """
        构建预定义的system prompt
        """
        system_prompt = f"""You are now a {dialect} data analyst, and you are given a database schema as follows:

【Schema】
{db_schema}

Please read and understand the database schema carefully, and generate an executable SQL based on the user's question and evidence. The generated SQL is protected by ```sql and ```.

Requirements:
1. Use {dialect} syntax for the SQL query
2. Only use tables and columns that exist in the provided schema
3. Make sure the SQL is syntactically correct and executable
4. If the question cannot be answered with the given schema, explain why
5. Include appropriate WHERE clauses, JOINs, and aggregations as needed
6. Always wrap the final SQL query in ```sql and ``` code blocks
"""

        return system_prompt
