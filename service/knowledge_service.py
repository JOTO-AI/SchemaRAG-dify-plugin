import requests
import logging
from typing import Optional, List


class KnowledgeService:
    """
    知识库服务类 - 负责与Dify知识库API交互，检索相关文档内容
    """

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

    def retrieve_schema_from_dataset(
        self,
        dataset_id: str,
        query: str,
        top_k: int = 5,
        retrieval_model: str = "semantic_search",
    ) -> str:
        """
        从Dify知识库检索相关的schema信息

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

            headers = {
                "Authorization": f"Bearer {self.api_key}",
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

            self.logger.info(f"正在从数据集 {dataset_id} 检索内容，查询: {query}")
            response = requests.post(url, headers=headers, json=data, timeout=30)

            if response.status_code == 200:
                result = response.json()

                # 提取检索到的内容
                schema_contents = []
                if "records" in result:
                    for record in result["records"]:
                        if "segment" in record and "content" in record["segment"]:
                            schema_contents.append(record["segment"]["content"])

                content = "\\n\\n".join(schema_contents)
                self.logger.info(f"成功检索到 {len(schema_contents)} 个相关片段")
                return content
            else:
                self.logger.warning(
                    f"检索API请求失败，状态码: {response.status_code}，尝试备选方法"
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
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            self.logger.info(f"使用备选方法获取数据集 {dataset_id} 的文档列表")
            response = requests.get(url, headers=headers, timeout=30)

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

            self.logger.warning(f"获取文档列表失败，状态码: {response.status_code}")
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
            headers = {
                "Authorization": f"Bearer {self.api_key}",
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
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                return response.json()
            else:
                self.logger.warning(
                    f"获取数据集信息失败，状态码: {response.status_code}"
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
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                result = response.json()
                return result.get("data", [])
            else:
                self.logger.warning(
                    f"获取数据集列表失败，状态码: {response.status_code}"
                )
                return []

        except Exception as e:
            self.logger.error(f"获取数据集列表时发生错误: {str(e)}")
            return []
