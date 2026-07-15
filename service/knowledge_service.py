import logging
import asyncio
import httpx
from typing import Optional, List, Tuple

from service.cache import cacheable, normalize_query, create_cache_key_from_dict


class KnowledgeService:
    """
    知识库服务类 - 负责与Dify知识库API交互，检索相关文档内容
    
    已集成缓存功能：
    - Schema检索结果自动缓存
    - 缓存键基于查询参数生成
    - 支持缓存失效和统计
    """

    DEFAULT_TIMEOUT = 30.0
    DEFAULT_RETRIEVAL_MODEL = "semantic_search"
    SUPPORTED_RETRIEVAL_MODELS = {
        "semantic_search",
        "keyword_search",
        "hybrid_search",
        "full_text_search",
    }

    def __init__(self, api_uri: str, api_key: str):
        """
        初始化知识库服务

        Args:
            api_uri: Dify API的基础URL
            api_key: API密钥
        """
        self.api_uri = api_uri.rstrip("/")
        self.api_key = api_key
        self.logger = logging.getLogger(__name__)

    def _headers(self) -> dict:
        """构建 Dify 知识库 API 请求头。"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """发送 HTTP 请求，避免内网 Dify API 被环境代理劫持。"""
        with httpx.Client(timeout=self.DEFAULT_TIMEOUT, trust_env=False) as client:
            return client.request(method, url, headers=self._headers(), **kwargs)

    def _format_response_error(self, response: httpx.Response) -> str:
        """提取 Dify 错误响应，避免日志只有状态码。"""
        try:
            error_data = response.json()
        except Exception:
            return response.text[:500] if response.text else "无响应内容"

        if isinstance(error_data, dict):
            code = error_data.get("code")
            message = error_data.get("message") or error_data.get("error")
            if code and message:
                return f"{code}: {message}"
            if message:
                return str(message)
        return str(error_data)[:500]

    def _default_retrieval_model(self, top_k: int, retrieval_model: str) -> dict:
        """构建 Dify 官方 RetrievalModel 的保守默认值。"""
        search_method = (
            retrieval_model
            if retrieval_model in self.SUPPORTED_RETRIEVAL_MODELS
            else self.DEFAULT_RETRIEVAL_MODEL
        )
        return {
            "search_method": search_method,
            "reranking_enable": False,
            "reranking_model": {
                "reranking_provider_name": "",
                "reranking_model_name": "",
            },
            "top_k": top_k,
            "score_threshold_enabled": False,
        }

    def _get_dataset_retrieval_model(self, dataset_id: str) -> Optional[dict]:
        """读取知识库自身保存的检索配置。失败时返回 None，交给默认配置兜底。"""
        url = f"{self.api_uri}/datasets/{dataset_id}"
        try:
            response = self._request("GET", url)
            if response.status_code != 200:
                self.logger.warning(
                    "读取知识库检索配置失败，状态码: %s，响应: %s",
                    response.status_code,
                    self._format_response_error(response),
                )
                return None

            dataset_info = response.json()
            retrieval_model = dataset_info.get("retrieval_model_dict") or dataset_info.get(
                "retrieval_model"
            )
            return retrieval_model if isinstance(retrieval_model, dict) else None
        except Exception as e:
            self.logger.warning(f"读取知识库检索配置异常: {str(e)}")
            return None

    def _build_retrieval_model(
        self,
        dataset_retrieval_model: Optional[dict],
        top_k: int,
        retrieval_model: str,
    ) -> dict:
        """
        合并检索配置。

        默认情况下沿用 Dify 知识库已保存的 search_method、rerank、权重和阈值，
        只覆盖 top_k；用户显式选择非默认检索方式时再覆盖 search_method。
        """
        if isinstance(dataset_retrieval_model, dict) and dataset_retrieval_model:
            model = dict(dataset_retrieval_model)
        else:
            model = self._default_retrieval_model(top_k, retrieval_model)

        search_method = model.get("search_method")
        if search_method not in self.SUPPORTED_RETRIEVAL_MODELS:
            model["search_method"] = self.DEFAULT_RETRIEVAL_MODEL

        if (
            retrieval_model in self.SUPPORTED_RETRIEVAL_MODELS
            and retrieval_model != self.DEFAULT_RETRIEVAL_MODEL
        ):
            model["search_method"] = retrieval_model

        model["top_k"] = top_k
        model.setdefault("reranking_enable", False)
        model.setdefault("score_threshold_enabled", False)

        if not model.get("reranking_enable"):
            model.setdefault(
                "reranking_model",
                {"reranking_provider_name": "", "reranking_model_name": ""},
            )

        return model

    def _build_retrieve_payload(
        self,
        dataset_id: str,
        query: str,
        top_k: int,
        retrieval_model: str,
    ) -> dict:
        dataset_retrieval_model = self._get_dataset_retrieval_model(dataset_id)
        return {
            "query": query,
            "retrieval_model": self._build_retrieval_model(
                dataset_retrieval_model,
                top_k,
                retrieval_model,
            ),
        }

    async def _get_dataset_retrieval_model_async(
        self,
        client: httpx.AsyncClient,
        dataset_id: str,
    ) -> Optional[dict]:
        """异步读取知识库自身保存的检索配置。"""
        url = f"{self.api_uri}/datasets/{dataset_id}"
        try:
            response = await client.get(url, headers=self._headers())
            if response.status_code != 200:
                self.logger.warning(
                    "异步读取知识库检索配置失败，状态码: %s，响应: %s",
                    response.status_code,
                    self._format_response_error(response),
                )
                return None

            dataset_info = response.json()
            retrieval_model = dataset_info.get("retrieval_model_dict") or dataset_info.get(
                "retrieval_model"
            )
            return retrieval_model if isinstance(retrieval_model, dict) else None
        except Exception as e:
            self.logger.warning(f"异步读取知识库检索配置异常: {str(e)}")
            return None

    def _extract_schema_contents(self, result: dict) -> str:
        """从 Dify 检索结果中提取片段内容。"""
        schema_contents = []
        if "records" in result:
            for record in result["records"]:
                if "segment" in record and "content" in record["segment"]:
                    schema_contents.append(record["segment"]["content"])

        return "\\n\\n".join(schema_contents)

    def retrieve_schema_from_multiple_datasets(
        self,
        dataset_ids: str,
        query: str,
        top_k: int = 5,
        retrieval_model: str = "semantic_search",
    ) -> str:
        """
        从多个Dify知识库异步并发检索相关的schema信息
        
        Args:
            dataset_ids: 数据集ID，支持逗号分隔的多个ID
            query: 查询内容
            top_k: 每个知识库返回结果数量
            retrieval_model: 检索模型类型
            
        Returns:
            检索到的schema内容，多个内容之间用\\n\\n分隔
        """
        # 解析数据集ID列表
        id_list = [id.strip() for id in dataset_ids.split(",") if id.strip()]
        
        if not id_list:
            self.logger.warning("数据集ID列表为空")
            return ""
        
        if len(id_list) == 1:
            # 单个知识库，使用原有方法
            return self.retrieve_schema_from_dataset(
                id_list[0], query, top_k, retrieval_model
            )
        
        # 多个知识库，使用异步并发检索
        self.logger.info(f"开始从 {len(id_list)} 个知识库并发检索: {id_list}")
        
        try:
            # 使用事件循环运行异步任务
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                results = loop.run_until_complete(
                    self._retrieve_from_multiple_datasets_async(
                        id_list, query, top_k, retrieval_model
                    )
                )
            finally:
                loop.close()
            
            # 合并结果
            all_content = []
            for dataset_id, content in results:
                if content and content.strip():
                    all_content.append(f"=== 知识库 {dataset_id} ===\\n{content}")
                    self.logger.info(f"知识库 {dataset_id}: 检索到内容长度 {len(content)}")
                else:
                    self.logger.warning(f"知识库 {dataset_id}: 未检索到内容")
            
            final_content = "\\n\\n".join(all_content)
            self.logger.info(f"多知识库检索完成，总内容长度: {len(final_content)}")
            return final_content
            
        except Exception as e:
            self.logger.error(f"多知识库检索异常: {str(e)}")
            # 降级到同步逐个检索
            return self._fallback_retrieve_multiple_datasets(
                id_list, query, top_k, retrieval_model
            )

    async def _retrieve_from_multiple_datasets_async(
        self,
        dataset_ids: List[str],
        query: str,
        top_k: int,
        retrieval_model: str,
    ) -> List[Tuple[str, str]]:
        """
        异步并发从多个数据集检索内容
        
        Args:
            dataset_ids: 数据集ID列表
            query: 查询内容
            top_k: 每个知识库返回结果数量
            retrieval_model: 检索模型类型
            
        Returns:
            检索结果列表，每项为 (dataset_id, content) 元组
        """
        timeout = httpx.Timeout(self.DEFAULT_TIMEOUT)
        
        async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
            # 创建并发任务
            tasks = [
                self._retrieve_from_single_dataset_async(
                    client, dataset_id, query, top_k, retrieval_model
                )
                for dataset_id in dataset_ids
            ]
            
            # 等待所有任务完成
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            final_results = []
            for i, result in enumerate(results):
                dataset_id = dataset_ids[i]
                if isinstance(result, Exception):
                    self.logger.error(f"知识库 {dataset_id} 检索异常: {str(result)}")
                    final_results.append((dataset_id, ""))
                else:
                    final_results.append((dataset_id, result))
            
            return final_results

    async def _retrieve_from_single_dataset_async(
        self,
        client: httpx.AsyncClient,
        dataset_id: str,
        query: str,
        top_k: int,
        retrieval_model: str,
    ) -> str:
        """
        异步从单个数据集检索内容
        
        Args:
            client: httpx异步客户端
            dataset_id: 数据集ID
            query: 查询内容
            top_k: 返回结果数量
            retrieval_model: 检索模型类型
            
        Returns:
            检索到的内容
        """
        url = f"{self.api_uri}/datasets/{dataset_id}/retrieve"
        dataset_retrieval_model = await self._get_dataset_retrieval_model_async(
            client,
            dataset_id,
        )
        data = {
            "query": query,
            "retrieval_model": self._build_retrieval_model(
                dataset_retrieval_model,
                top_k,
                retrieval_model,
            ),
        }
        
        try:
            response = await client.post(url, headers=self._headers(), json=data)
            if response.status_code == 200:
                return self._extract_schema_contents(response.json())
            else:
                self.logger.warning(
                    "数据集 %s 检索失败，状态码: %s，响应: %s",
                    dataset_id,
                    response.status_code,
                    self._format_response_error(response),
                )
                return ""
                
        except Exception as e:
            self.logger.error(f"数据集 {dataset_id} 异步检索异常: {str(e)}")
            return ""

    def _fallback_retrieve_multiple_datasets(
        self,
        dataset_ids: List[str],
        query: str,
        top_k: int,
        retrieval_model: str,
    ) -> str:
        """
        降级方案：同步逐个检索多个数据集
        
        Args:
            dataset_ids: 数据集ID列表
            query: 查询内容
            top_k: 每个知识库返回结果数量
            retrieval_model: 检索模型类型
            
        Returns:
            检索到的schema内容
        """
        self.logger.info("使用降级方案进行同步检索")
        
        all_content = []
        for dataset_id in dataset_ids:
            try:
                content = self.retrieve_schema_from_dataset(
                    dataset_id, query, top_k, retrieval_model
                )
                if content and content.strip():
                    all_content.append(f"=== 知识库 {dataset_id} ===\\n{content}")
            except Exception as e:
                self.logger.error(f"数据集 {dataset_id} 同步检索异常: {str(e)}")
        
        return "\\n\\n".join(all_content)

    @cacheable(
        name="schema_cache",
        key_prefix="schema",
        ttl=3600,  # 1小时过期
        key_generator=lambda self, dataset_id, query, top_k=5, retrieval_model="semantic_search":
            create_cache_key_from_dict(
                "schema",
                {
                    "dataset_id": dataset_id,
                    "query": normalize_query(query),
                    "top_k": top_k,
                    "retrieval_model": retrieval_model
                }
            ),
        condition=lambda result: result and result.strip()  # 只缓存非空结果
    )
    def retrieve_schema_from_dataset(
        self,
        dataset_id: str,
        query: str,
        top_k: int = 5,
        retrieval_model: str = "semantic_search",
    ) -> str:
        """
        从Dify知识库检索相关的schema信息
        
        该方法已启用缓存功能：
        - 相同参数的查询将直接返回缓存结果
        - 缓存有效期为1小时
        - 查询会被规范化以提高缓存命中率

        Args:
            dataset_id: 数据集ID
            query: 查询内容
            top_k: 返回结果数量
            retrieval_model: 检索模型类型

        Returns:
            检索到的schema内容，多个内容之间用\\n\\n分隔
        """
        try:
            # 构建检索API URL
            url = f"{self.api_uri}/datasets/{dataset_id}/retrieve"

            data = self._build_retrieve_payload(
                dataset_id,
                query,
                top_k,
                retrieval_model,
            )

            self.logger.info(f"正在从数据集 {dataset_id} 检索内容，查询: {query}")
            response = self._request("POST", url, json=data)

            if response.status_code == 200:
                content = self._extract_schema_contents(response.json())
                segment_count = len(content.split("\\n\\n")) if content else 0
                self.logger.info(f"成功检索到 {segment_count} 个相关片段")
                return content
            else:
                self.logger.warning(
                    "检索API请求失败，状态码: %s，响应: %s，尝试备选方法",
                    response.status_code,
                    self._format_response_error(response),
                )
                # 如果检索API失败，尝试使用文档片段API作为备选
                return self._fallback_retrieve_documents(dataset_id)

        except Exception as e:
            self.logger.error(f"检索schema时发生错误: {str(e)}")
            # 如果出错，尝试备选方法
            return self._fallback_retrieve_documents(dataset_id)

    def _fallback_retrieve_documents(self, dataset_id: str) -> str:
        """
        备选方法：获取数据集中的文档信息

        Args:
            dataset_id: 数据集ID

        Returns:
            获取到的文档内容
        """
        try:
            # 首先获取数据集中的文档列表
            url = f"{self.api_uri}/datasets/{dataset_id}/documents"

            self.logger.info(f"使用备选方法获取数据集 {dataset_id} 的文档列表")
            response = self._request("GET", url)

            if response.status_code == 200:
                documents = response.json()
                schema_contents = []

                # 获取前几个文档的片段
                if "data" in documents:
                    for doc in documents["data"][:3]:  # 限制获取前3个文档
                        doc_id = doc.get("id")
                        if doc_id:
                            segments = self._get_document_segments(dataset_id, doc_id)
                            if segments:
                                schema_contents.extend(segments)

                content = "\\n\\n".join(schema_contents)
                self.logger.info(
                    f"通过备选方法获取到 {len(schema_contents)} 个文档片段"
                )
                return content

            self.logger.warning(
                "获取文档列表失败，状态码: %s，响应: %s",
                response.status_code,
                self._format_response_error(response),
            )
            return ""

        except Exception as e:
            self.logger.error(f"备选检索方法失败: {str(e)}")
            return ""

    def _get_document_segments(self, dataset_id: str, document_id: str) -> List[str]:
        """
        获取文档的片段内容

        Args:
            dataset_id: 数据集ID
            document_id: 文档ID

        Returns:
            文档片段内容列表
        """
        try:
            url = (
                f"{self.api_uri}/datasets/{dataset_id}/documents/{document_id}/segments"
            )

            response = self._request("GET", url)

            if response.status_code == 200:
                result = response.json()
                segments = []

                if "data" in result:
                    for segment in result["data"][:5]:  # 限制每个文档最多5个片段
                        if "content" in segment and segment["content"]:
                            segments.append(segment["content"])

                return segments

            return []

        except Exception as e:
            self.logger.error(f"获取文档 {document_id} 片段失败: {str(e)}")
            return []

    def get_dataset_info(self, dataset_id: str) -> Optional[dict]:
        """
        获取数据集基本信息

        Args:
            dataset_id: 数据集ID

        Returns:
            数据集信息字典，如果失败返回None
        """
        try:
            url = f"{self.api_uri}/datasets/{dataset_id}"

            response = self._request("GET", url)

            if response.status_code == 200:
                return response.json()
            else:
                self.logger.warning(
                    "获取数据集信息失败，状态码: %s，响应: %s",
                    response.status_code,
                    self._format_response_error(response),
                )
                return None

        except Exception as e:
            self.logger.error(f"获取数据集信息时发生错误: {str(e)}")
            return None

    def list_datasets(self) -> List[dict]:
        """
        列出所有可用的数据集

        Returns:
            数据集列表
        """
        try:
            url = f"{self.api_uri}/datasets"

            response = self._request("GET", url)

            if response.status_code == 200:
                result = response.json()
                return result.get("data", [])
            else:
                self.logger.warning(
                    "获取数据集列表失败，状态码: %s，响应: %s",
                    response.status_code,
                    self._format_response_error(response),
                )
                return []

        except Exception as e:
            self.logger.error(f"获取数据集列表时发生错误: {str(e)}")
            return []
