"""
Dify服务模块
"""

import os
import logging
from typing import Dict
import sys

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)  # 添加上级目录到路径中

from config import DifyUploadConfig

# 尝试导入dify客户端，如果失败则在需要时处理
try:
    from core.dify.dify_client import KnowledgeBaseClient
except ImportError:
    KnowledgeBaseClient = None


class DifyUploader:
    """Dify文件上传器"""

    def __init__(self, config: DifyUploadConfig, logger: logging.Logger):
        if KnowledgeBaseClient is None:
            raise ImportError(
                "Dify client is not installed. Please install it to use the upload feature."
            )
        self.config = config
        self.logger = logger
        self.client = KnowledgeBaseClient(
            api_key=config.api_key, base_url=config.base_url
        )
        self._dataset_cache: Dict[str, str] = {}

    def _get_or_create_dataset(self, dataset_name: str) -> str:
        """获取或创建Dify数据集"""
        if dataset_name in self._dataset_cache:
            self.logger.info(f"从缓存中获取数据集ID: {dataset_name}")
            return self._dataset_cache[dataset_name]

        # 首先尝试查找现有数据集
        def try_find_existing_dataset():
            try:
                response_data = self.client.list_datasets().json()
                datasets = response_data.get("data", [])
                for dataset in datasets:
                    if dataset.get("name") == dataset_name:
                        dataset_id = dataset.get("id")
                        self.logger.info(
                            f"找到现有数据集: {dataset_name} (ID: {dataset_id})"
                        )
                        self._dataset_cache[dataset_name] = dataset_id
                        return dataset_id
                return None
            except Exception as e:
                self.logger.warning(f"查找现有数据集时出错: {e}")
                return None

        # 第一次尝试查找现有数据集
        existing_dataset_id = try_find_existing_dataset()
        if existing_dataset_id:
            return existing_dataset_id

        # 如果没找到，尝试创建新数据集
        self.logger.info(f"未找到现有数据集，将创建新数据集: {dataset_name}")
        try:
            response_data = self.client.create_dataset(
                name=dataset_name,
                description=f"数据库 {dataset_name} 的schema信息",
                permission=self.config.permission,
                indexing_technique=self.config.indexing_technique,
            ).json()
            dataset_id = response_data.get("id")
            if not dataset_id:
                raise Exception(f"创建数据集成功但未返回ID. 响应: {response_data}")
            self.logger.info(f"成功创建数据集: {dataset_name} (ID: {dataset_id})")
            self._dataset_cache[dataset_name] = dataset_id
            return dataset_id
        except Exception as e:
            # 如果创建失败且错误提示数据集已存在，再次尝试查找
            if "already exists" in str(e) or "409" in str(e):
                self.logger.info(f"数据集 {dataset_name} 已存在，重新查找...")
                existing_dataset_id = try_find_existing_dataset()
                if existing_dataset_id:
                    return existing_dataset_id
                else:
                    # 如果还是找不到，可能是权限问题或其他问题，但不应该抛出异常
                    # 因为数据集确实存在，只是我们无法访问它
                    self.logger.warning(f"数据集 {dataset_name} 应该存在但无法找到，可能存在权限问题")
                    # 尝试使用数据集名称作为最后的手段
                    raise Exception(f"数据集 {dataset_name} 已存在但无法获取其ID，请检查权限设置")
            
            self.logger.error(f"创建数据集 {dataset_name} 失败: {e}")
            raise

    def upload_file(self, file_path: str):
        """上传单个文件到指定的数据集"""
        dataset_name = os.path.splitext(os.path.basename(file_path))[0]
        self.logger.info(f"准备上传文件 '{file_path}' 到数据集 '{dataset_name}'")
        try:
            if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                self.logger.error(f"文件不存在或为空，跳过上传: {file_path}")
                return

            dataset_id = self._get_or_create_dataset(dataset_name)
            self.client.dataset_id = dataset_id

            extra_params = {
                "indexing_technique": self.config.indexing_technique,
                "process_rule": {
                    "rules": {
                        "pre_processing_rules": [
                            {"id": "remove_extra_spaces", "enabled": False},
                            {"id": "remove_urls_emails", "enabled": True},
                        ],
                        "segmentation": {
                            "separator": "\n\n",
                            "max_tokens": int(self.config.max_tokens),
                        },
                    },
                    "mode": self.config.process_mode,
                },
            }
            self.logger.info(f"开始上传文件: {file_path} -> 数据集ID: {dataset_id}")
            response = self.client.create_document_by_file(
                file_path=file_path, extra_params=extra_params
            )

            # 检查HTTP响应状态，如果不是2xx，则会引发异常
            response.raise_for_status()

            response_data = response.json()
            doc_id = response_data.get("document", {}).get("id", "N/A")
            self.logger.info(
                f"✓ 成功上传: {os.path.basename(file_path)} -> 数据集: {dataset_name} (文档ID: {doc_id})"
            )

        except Exception as e:
            self.logger.error(f"✗ 上传文件 '{file_path}' 失败: {str(e)}")
            raise

    def upload_text(self, name: str, content: str):
        """上传文本内容到指定的数据集"""
        dataset_name = name
        self.logger.info(f"准备上传文本内容到数据集 '{dataset_name}'")
        try:
            dataset_id = self._get_or_create_dataset(dataset_name)
            self.client.dataset_id = dataset_id

            extra_params = {
                "indexing_technique": self.config.indexing_technique,
                "process_rule": {
                    "rules": {
                        "pre_processing_rules": [
                            {"id": "remove_extra_spaces", "enabled": False},
                            {"id": "remove_urls_emails", "enabled": True},
                        ],
                        "segmentation": {
                            "separator": "\n#",
                            "max_tokens": int(self.config.max_tokens),
                        },
                    },
                    "mode": self.config.process_mode,
                },
            }
            response = self.client.create_document_by_text(
                name=name, text=content, extra_params=extra_params
            )

            # 检查HTTP响应状态，如果不是2xx，则会引发异常
            response.raise_for_status()

            response_data = response.json()
            doc_id = response_data.get("document", {}).get("id", "N/A")
            self.logger.info(
                f"✓ 成功上传: {name} -> 数据集: {dataset_name} (文档ID: {doc_id})"
            )

        except Exception as e:
            self.logger.error(f"✗ 上传文件 '{name}' 失败: {str(e)}")
            raise


if __name__ == "__main__":
    # 示例：如何使用DifyUploader
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("DifyUploader")
    dify_config = DifyUploadConfig()
    uploader = DifyUploader(config=dify_config, logger=logger)
    try:
        # 假设有一个文件需要上传
        # file_to_upload = "C:\\Users\\cp-jiangweijun\\Desktop\\schemaRAG_builder\\output\\schema.txt"
        # uploader.upload_file(file_to_upload)

        content = "这是一个测试文本内容，用于上传到Dify知识库。"
        uploader.upload_text(name="测试文本", content=content)

    except Exception as e:
        logger.error(f"上传过程中发生错误: {e}")
