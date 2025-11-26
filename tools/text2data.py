from collections.abc import Generator
from typing import Any, Optional, List, Dict
import sys
import os
import re
import logging
from prompt import text2sql_prompt, summary_prompt
from service.knowledge_service import KnowledgeService
from service.database_service import DatabaseService
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.entities.model.message import SystemPromptMessage, UserPromptMessage
from dify_plugin.config.logger_format import plugin_logger_handler

# 添加项目根目录到Python路径，以便导入service模块
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class Text2DataTool(Tool):
    """
    Text to Data Tool - Convert natural language questions to SQL queries and execute them to return data
    
    功能特性:
    1. 多知识库检索支持 - 支持从多个知识库同时检索schema信息
    2. 示例知识库支持 - 支持检索SQL示例以提高生成质量
    3. SQL安全策略 - 防止危险的SQL操作
    4. 最大行数限制 - 防止返回过多数据
    5. 数值格式化 - 避免科学计数法显示
    """
    
    # 性能和安全相关常量
    DEFAULT_TOP_K = 5
    DEFAULT_DIALECT = "mysql"
    DEFAULT_RETRIEVAL_MODEL = "semantic_search"
    DEFAULT_MAX_ROWS = 500
    MAX_CONTENT_LENGTH = 10000  # 最大输入内容长度
    DECIMAL_PLACES = 2  # 小数位数

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 初始化知识库服务
        self.api_uri = self.runtime.credentials.get("api_uri")
        self.dataset_api_key = self.runtime.credentials.get("dataset_api_key")
        self.knowledge_service = KnowledgeService(self.api_uri, self.dataset_api_key)
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(plugin_logger_handler)

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
            # 获取参数并设置默认值
            dataset_id = tool_parameters.get("dataset_id")
            llm_model = tool_parameters.get("llm")
            content = tool_parameters.get("content")
            dialect = tool_parameters.get("dialect", self.DEFAULT_DIALECT)
            top_k = tool_parameters.get("top_k", self.DEFAULT_TOP_K)
            retrieval_model = tool_parameters.get("retrieval_model", self.DEFAULT_RETRIEVAL_MODEL)
            output_format = tool_parameters.get("output_format", "json")
            max_rows = tool_parameters.get("max_rows", self.DEFAULT_MAX_ROWS)
            example_dataset_id = tool_parameters.get("example_dataset_id")

            # 验证必要参数
            if not dataset_id:
                self.logger.error("错误: 缺少知识库ID")
                raise ValueError("缺少知识库ID")

            if not content:
                self.logger.error("错误: 缺少问题内容")
                raise ValueError("缺少问题内容")
            
            # 验证内容长度
            if len(content) > self.MAX_CONTENT_LENGTH:
                self.logger.error(f"错误: 问题内容过长，最大长度为 {self.MAX_CONTENT_LENGTH}")
                raise ValueError(f"问题内容过长，最大长度为 {self.MAX_CONTENT_LENGTH}")

            if not llm_model:
                self.logger.error("错误: 缺少LLM模型配置")
                raise ValueError("缺少LLM模型配置")

            if not self.api_uri or not self.dataset_api_key:
                self.logger.error("错误: 缺少API配置信息")
                raise ValueError("API配置无效")

            # 验证数据库配置
            if not all([self.db_type, self.db_host, self.db_port, self.db_user, self.db_password, self.db_name]):
                self.logger.error("错误: 数据库配置不完整")
                raise ValueError("数据库配置无效")
            
            # 验证max_rows参数
            if not isinstance(max_rows, int) or max_rows < 1:
                self.logger.warning(f"无效的max_rows值: {max_rows}，使用默认值 {self.DEFAULT_MAX_ROWS}")
                max_rows = self.DEFAULT_MAX_ROWS

            # 步骤1: 使用多知识库检索相关的schema信息
            self.logger.info(f"从知识库 {dataset_id} 检索架构信息，查询长度: {len(content)}")

            try:
                # 使用多知识库检索功能
                schema_info = self.knowledge_service.retrieve_schema_from_multiple_datasets(
                    dataset_id, content, top_k, retrieval_model
                )
            except Exception as e:
                self.logger.error(f"检索架构信息时发生错误: {str(e)}")
                schema_info = "未找到相关的数据库架构信息"

            if not schema_info or not schema_info.strip():
                self.logger.warning("未从知识库检索到相关的架构信息")
                schema_info = "未找到相关的数据库架构信息"

            # 步骤2: 检索示例信息（如果提供了示例知识库ID）
            example_info = ""
            if example_dataset_id and example_dataset_id.strip():
                self.logger.info(f"从示例知识库 {example_dataset_id} 检索示例信息")
                try:
                    example_info = self.knowledge_service.retrieve_schema_from_multiple_datasets(
                        example_dataset_id, content, top_k, retrieval_model
                    )
                    if example_info and example_info.strip():
                        self.logger.info(f"检索到示例信息，长度: {len(example_info)}")
                    else:
                        self.logger.info("未检索到相关的示例信息")
                except Exception as e:
                    self.logger.warning(f"检索示例信息时发生错误: {str(e)}")
                    example_info = ""

            # 步骤3: 构建预定义的prompt并生成SQL
            self.logger.info("正在生成SQL查询...")

            try:
                system_prompt = text2sql_prompt._build_system_prompt(dialect=dialect)
                user_prompt = text2sql_prompt._build_user_prompt(
                    db_schema=schema_info,
                    question=content,
                    example_info=example_info
                )

                response = self.session.model.llm.invoke(
                    model_config=llm_model,
                    prompt_messages=[
                        SystemPromptMessage(content=system_prompt),
                        UserPromptMessage(content=user_prompt),
                    ],
                    stream=False,
                )

                sql_query = ""
                if hasattr(response, "message") and response.message:
                    sql_query = response.message.content.strip() if response.message.content else ""

                if not sql_query:
                    self.logger.error("错误: 无法生成SQL查询")
                    raise ValueError("生成的SQL查询为空")

                # 清理并验证SQL查询（应用安全策略）
                sql_query = self._clean_and_validate_sql(sql_query)

                if not sql_query or not sql_query.strip():
                    self.logger.error("错误: 生成的SQL查询为空或无效")
                    raise ValueError("生成的SQL查询为空或无效")

            except Exception as e:
                self.logger.error(f"生成SQL查询时发生错误: {str(e)}")
                raise

            # 步骤4: 执行SQL查询
            self.logger.info("正在执行SQL查询...")

            try:
                results, columns = self.db_service.execute_query(
                    self.db_type, self.db_host, self.db_port,
                    self.db_user, self.db_password, self.db_name, sql_query
                )
            except Exception as e:
                self.logger.error(f"执行SQL查询时发生错误: {str(e)}")
                raise

            # 早期检查结果
            result_count = len(results)
            if result_count == 0:
                yield self.create_text_message("查询执行成功，但没有返回数据")
                return

            # 检查结果大小，应用最大行数限制
            if result_count > max_rows:
                self.logger.warning(f"警告: 查询返回了 {result_count} 行数据，结果已截断到 {max_rows} 行")
                results = results[:max_rows]

            # 格式化数值，避免科学计数法
            formatted_results = self._format_numeric_values(results)

            # 步骤5: 格式化输出
            if output_format == "summary":
                yield from self._handle_summary_output(formatted_results, columns, content, llm_model)
            else:
                try:
                    formatted_output = self.db_service._format_output(formatted_results, columns, output_format)
                    yield self.create_text_message(text=formatted_output)
                except Exception as e:
                    self.logger.error(f"格式化输出时发生错误: {str(e)}")
                    raise ValueError(f"格式化输出时发生错误: {str(e)}")

            self.logger.info(f"SQL查询结果处理完成，返回 {len(results)} 行数据")

        except Exception as e:
            self.logger.error(f"执行过程中发生错误: {str(e)}")
            raise ValueError(f"执行过程中发生错误: {str(e)}")

    def _handle_summary_output(self, formatted_results: List[Dict], columns: List[str], 
                               content: str, llm_model: Any) -> Generator[ToolInvokeMessage]:
        """处理摘要输出格式"""
        self.logger.info("正在生成数据摘要...")
        
        try:
            json_data = self.db_service._format_output(formatted_results, columns, "json")
            
            if not json_data or json_data.strip() == "":
                self.logger.warning("警告: 查询结果为空，无法生成摘要")
                return
            
            summary_system_prompt = summary_prompt._data_summary_prompt(json_data, content)
            
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
            
            if not summary_result and hasattr(summary_response, "message") and summary_response.message:
                summary_result = summary_response.message.content
                if summary_result:
                    yield self.create_text_message(text=summary_result)
        
        except Exception as e:
            self.logger.error(f"生成摘要时发生错误: {str(e)}")
            try:
                formatted_output = self.db_service._format_output(formatted_results, columns, "json")
                self.logger.warning("摘要生成失败，返回原始数据")
                yield self.create_text_message(text=formatted_output)
            except Exception as e2:
                self.logger.error(f"数据格式化也失败了: {str(e2)}")
                raise

    def _clean_and_validate_sql(self, sql_query: str) -> Optional[str]:
        """清理和验证SQL查询，使用正则黑名单模式，禁止危险操作"""
        if not sql_query:
            return None

        try:
            # 清理 markdown 格式
            markdown_pattern = re.compile(r"```(?:sql)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
            match = markdown_pattern.search(sql_query)
            cleaned_sql = match.group(1).strip() if match else sql_query.strip()
            if not cleaned_sql:
                return None

            # 移除多余空白
            cleaned_sql = re.sub(r"\s+", " ", cleaned_sql).strip()
            sql_lower = cleaned_sql.lower()

            # 黑名单模式：禁止危险的SQL操作
            dangerous_patterns = [
                r'^\s*(drop|delete|truncate|update|insert|create|alter|grant|revoke)\s+',
                r'\b(exec|execute|sp_|xp_)\b',
                r'\b(into\s+outfile|load_file|load\s+data)\b',
                r'\b(union\s+all\s+select.*into|select.*into)\b',
                r';\s*(drop|delete|truncate|update|insert|create|alter)',
                r'\b(benchmark|sleep|waitfor|delay)\b',
                r'@@|information_schema\.(?!columns|tables|schemata)',
            ]

            # 检查是否包含危险模式
            for pattern in dangerous_patterns:
                if re.search(pattern, sql_lower, re.IGNORECASE):
                    raise ValueError(f"检测到危险的SQL操作，查询被拒绝")

            return cleaned_sql

        except ValueError:
            raise
        except Exception as e:
            self.logger.warning(f"SQL清理失败: {str(e)}")
            return None

    def _format_numeric_values(self, results: List[Dict]) -> List[Dict]:
        """格式化数值，避免科学计数法，保留指定小数位数"""
        if not results:
            return results

        formatted_results = []
        for row in results:
            formatted_row = {}
            for key, value in row.items():
                formatted_row[key] = self._format_single_value(value)
            formatted_results.append(formatted_row)

        self.logger.debug(f"数值格式化完成，处理了 {len(formatted_results)} 行数据")
        return formatted_results

    def _format_single_value(self, value) -> Any:
        """格式化单个值，优化性能和逻辑"""
        # 快速处理 None 和布尔值
        if value is None or isinstance(value, bool):
            return value

        # 处理字符串和其他非数值类型
        if not isinstance(value, (int, float)):
            return value

        try:
            # 处理整数
            if isinstance(value, int):
                return str(value)

            # 处理浮点数（包括 NaN 和无穷大）
            if isinstance(value, float):
                # 检查是否为有效数值
                if not (value == value):  # 检查 NaN
                    return None

                # 检查无穷大
                if abs(value) == float("inf"):
                    return str(value)

                # 检查是否为整数值（如 1.0, 2.0）
                if value.is_integer():
                    return str(int(value))
                else:
                    # 浮点数保留指定小数位数，避免科学计数法
                    return f"{value:.{self.DECIMAL_PLACES}f}"

            # 其他数值类型的安全处理
            return str(value)

        except (ValueError, OverflowError, TypeError, AttributeError):
            # 处理异常情况，保留原始值的字符串形式
            return str(value) if value is not None else None