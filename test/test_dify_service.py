#!/usr/bin/env python3
"""
测试 Dify 上传服务
"""

import logging
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import DifyUploadConfig  # noqa: E402
from service.dify_service import DifyUploader  # noqa: E402


class TestDifyUploader(unittest.TestCase):
    """Dify 上传服务测试"""

    def _response(self, data):
        """创建响应 Mock"""
        response = Mock()
        response.json.return_value = data
        return response

    def _create_uploader(self):
        """创建测试上传器"""
        config = DifyUploadConfig(
            api_key="dataset-key",
            base_url="http://dify.example/v1",
        )
        return DifyUploader(config, logging.getLogger("test.dify_uploader"))

    @patch("service.dify_service.KnowledgeBaseClient")
    def test_finds_existing_dataset_across_pages(self, client_class):
        """查找现有知识库时分页搜索所有可见数据集"""
        client = client_class.return_value
        client.list_datasets.side_effect = [
            self._response(
                {
                    "data": [{"id": "other-id", "name": "other_schema"}],
                    "page": 1,
                    "limit": 1,
                    "total": 2,
                    "has_more": True,
                }
            ),
            self._response(
                {
                    "data": [{"id": "target-id", "name": "haitian_schema"}],
                    "page": 2,
                    "limit": 1,
                    "total": 2,
                    "has_more": False,
                }
            ),
        ]
        uploader = self._create_uploader()

        dataset_id = uploader._get_or_create_dataset("haitian_schema")

        self.assertEqual(dataset_id, "target-id")
        self.assertEqual(client.list_datasets.call_count, 2)
        client.create_dataset.assert_not_called()

    @patch("service.dify_service.KnowledgeBaseClient")
    def test_conflict_creation_retries_paginated_lookup(self, client_class):
        """创建知识库撞名后重新分页查找已存在知识库"""
        client = client_class.return_value
        client.list_datasets.side_effect = [
            self._response(
                {
                    "data": [{"id": "other-id", "name": "other_schema"}],
                    "page": 1,
                    "limit": 1,
                    "total": 1,
                    "has_more": False,
                }
            ),
            self._response(
                {
                    "data": [{"id": "other-id", "name": "other_schema"}],
                    "page": 1,
                    "limit": 1,
                    "total": 2,
                    "has_more": True,
                }
            ),
            self._response(
                {
                    "data": [{"id": "target-id", "name": "haitian_schema"}],
                    "page": 2,
                    "limit": 1,
                    "total": 2,
                    "has_more": False,
                }
            ),
        ]
        client.create_dataset.side_effect = ValueError(
            "API请求失败: HTTP 409 - The dataset name already exists."
        )
        uploader = self._create_uploader()

        dataset_id = uploader._get_or_create_dataset("haitian_schema")

        self.assertEqual(dataset_id, "target-id")
        client.create_dataset.assert_called_once()


if __name__ == "__main__":
    unittest.main()
