from collections.abc import Generator
from typing import Any, Tuple, Union
import sys
import os
import logging
from prompt import text2sql_prompt
from service.knowledge_service import KnowledgeService
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.entities.model.message import SystemPromptMessage, UserPromptMessage

# 添加项目根目录到Python路径，以便导入service模块
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class Text2SQLTool(Tool):
    # 类级别的服务实例缓存
    _knowledge_service_cache = {}
    # 缓存大小限制，防止内存泄漏
    _cache_max_size = 10

    # 性能和配置常量
    DEFAULT_TOP_K = 5
    DEFAULT_DIALECT = "mysql"
    DEFAULT_RETRIEVAL_MODEL = "semantic_search"
    MAX_CONTENT_LENGTH = 10000  # 最大输入内容长度

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_uri = self.runtime.credentials.get("api_uri")
        self.dataset_api_key = self.runtime.credentials.get("dataset_api_key")
        self._knowledge_service = None
        self._config_validated = False
        self.logger = logging.getLogger(__name__)

        # 初始化时验证配置
        self._validate_config()

    @property
    def knowledge_service(self):
        """延迟初始化的知识服务实例，使用缓存避免重复创建"""
        if self._knowledge_service is None:
            # 使用API配置作为缓存键
            cache_key = f"{self.api_uri}:{self.dataset_api_key}"

            if cache_key not in self._knowledge_service_cache:
                # 如果缓存已满，清理最旧的条目
                if len(self._knowledge_service_cache) >= self._cache_max_size:
                    # 删除第一个（最旧的）条目
                    oldest_key = next(iter(self._knowledge_service_cache))
                    del self._knowledge_service_cache[oldest_key]

                self._knowledge_service_cache[cache_key] = KnowledgeService(
                    self.api_uri, self.dataset_api_key
                )

            self._knowledge_service = self._knowledge_service_cache[cache_key]

        return self._knowledge_service

    def _validate_config(self):
        """验证API配置"""
        self._config_validated = bool(self.api_uri and self.dataset_api_key)
        if not self._config_validated:
            self.logger.warning("API配置不完整")

    @classmethod
    def clear_cache(cls):
        """清理服务缓存，释放资源"""
        cls._knowledge_service_cache.clear()

    @classmethod
    def get_cache_size(cls) -> int:
        """获取当前缓存大小"""
        return len(cls._knowledge_service_cache)

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        """
        Convert natural language questions to SQL queries using database schema knowledge base
        """
        # 早期配置验证
        if not self._config_validated:
            logging.error("错误: 缺少API配置信息")
            raise ValueError("API配置无效")

        try:
            # 验证和获取参数
            params_result = self._validate_and_extract_parameters(tool_parameters)
            if isinstance(params_result, str):  # 错误消息
                logging.error(f"错误: {params_result}")
                raise ValueError(params_result)

            dataset_id, llm_model, content, dialect, top_k, retrieval_model, custom_prompt, example_dataset_id = (
                params_result
            )

            # 步骤1: 从知识库检索相关的schema信息
            self.logger.info(
                f"从知识库 {dataset_id} 检索架构信息，查询长度: {len(content)}"
            )

            # 使用新的多知识库检索功能
            schema_info = self.knowledge_service.retrieve_schema_from_multiple_datasets(
                dataset_id, content, top_k, retrieval_model
            )

            if not schema_info or not schema_info.strip():
                self.logger.warning("未检索到相关的架构信息")
                schema_info = "未找到相关的数据库架构信息"

            # 步骤2: 检索示例信息（如果提供了示例知识库ID）
            example_info = ""
            if example_dataset_id and example_dataset_id.strip():
                self.logger.info(f"从示例知识库 {example_dataset_id} 检索示例信息")
                example_info = self.knowledge_service.retrieve_schema_from_multiple_datasets(
                    example_dataset_id, content, top_k, retrieval_model
                )
                if example_info and example_info.strip():
                    self.logger.info(f"检索到示例信息，长度: {len(example_info)}")
                else:
                    self.logger.info("未检索到相关的示例信息")

            # 步骤3: 构建预定义的prompt（包含自定义提示和示例）
            system_prompt = text2sql_prompt._build_system_prompt(
                dialect, schema_info, content, custom_prompt, example_info
            )
            
            # 步骤4: 调用LLM生成SQL
            self.logger.info("开始调用LLM生成SQL查询")

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

            # 优化流式响应处理，避免内存累积
            has_streamed_content = False
            total_content_length = 0

            for chunk in response:
                if chunk.delta.message and chunk.delta.message.content:
                    sql_content = chunk.delta.message.content
                    has_streamed_content = True
                    total_content_length += len(sql_content)

                    # 防止过长的响应
                    if total_content_length > 50000:  # 50KB限制
                        logging.warning("警告: 响应内容过长，已截断")
                        break

                    yield self.create_text_message(text=sql_content)

            # 如果没有流式响应，尝试获取完整响应
            if (
                not has_streamed_content
                and hasattr(response, "message")
                and response.message
            ):
                yield self.create_text_message(text=response.message.content)

            self.logger.info(f"SQL生成完成，响应长度: {total_content_length}")

        except ValueError as e:
            self.logger.error(f"参数验证错误: {str(e)}")
            raise ValueError(f"参数错误: {str(e)}")
        except ConnectionError as e:
            self.logger.error(f"网络连接错误: {str(e)}")
            raise ValueError(f"网络连接错误: {str(e)}")
        except Exception as e:
            self.logger.error(f"SQL生成异常: {str(e)}")
            raise ValueError(f"SQL生成异常: {str(e)}")

    def _validate_and_extract_parameters(
        self, tool_parameters: dict[str, Any]
    ) -> Union[Tuple[str, Any, str, str, int, str, str, str], str]:
        """验证并提取工具参数，返回参数元组或错误消息"""
        # 验证必要参数
        dataset_id = tool_parameters.get("dataset_id")
        if not dataset_id or not dataset_id.strip():
            return "缺少知识库ID"

        llm_model = tool_parameters.get("llm")
        if not llm_model:
            return "缺少LLM模型配置"

        content = tool_parameters.get("content")
        if not content or not content.strip():
            return "缺少问题内容"

        # 检查内容长度
        if len(content) > self.MAX_CONTENT_LENGTH:
            return f"问题内容过长，最大允许 {self.MAX_CONTENT_LENGTH} 字符，当前 {len(content)} 字符"

        # 获取可选参数并设置默认值
        dialect = tool_parameters.get("dialect", self.DEFAULT_DIALECT)
        if dialect not in ["mysql", "postgresql", "sqlite", "oracle", "sqlserver", "mssql", "dameng", "doris"]:
            return f"不支持的数据库方言: {dialect}"

        top_k = tool_parameters.get("top_k", self.DEFAULT_TOP_K)
        try:
            top_k = int(top_k)
            if top_k <= 0 or top_k > 50:
                return "top_k 必须在 1-50 之间"
        except (ValueError, TypeError):
            return "top_k 必须是有效的整数"

        retrieval_model = tool_parameters.get(
            "retrieval_model", self.DEFAULT_RETRIEVAL_MODEL
        )
        if retrieval_model not in [
            "semantic_search",
            "keyword_search",
            "hybrid_search",
            "full_text_search",
        ]:
            return f"不支持的检索模型: {retrieval_model}"

        # 获取自定义提示词（可选参数）
        custom_prompt = tool_parameters.get("custom_prompt", "")
        if custom_prompt and not isinstance(custom_prompt, str):
            return "自定义提示词必须是字符串类型"

        # 限制自定义提示词长度防止过长
        if custom_prompt and len(custom_prompt) > 2000:
            return f"自定义提示词过长，最大允许 2000 字符，当前 {len(custom_prompt)} 字符"

        # 获取示例知识库ID（可选参数）
        example_dataset_id = tool_parameters.get("example_dataset_id", "")
        if example_dataset_id and not isinstance(example_dataset_id, str):
            return "示例知识库ID必须是字符串类型"

        return (
            dataset_id.strip(),
            llm_model,
            content.strip(),
            dialect,
            top_k,
            retrieval_model,
            custom_prompt.strip() if custom_prompt else "",
            example_dataset_id.strip() if example_dataset_id else "",
        )
