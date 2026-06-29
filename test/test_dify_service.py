#!/usr/bin/env python3
"""
测试 Dify 上传服务
"""

import logging
import os
import sys
import tempfile
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
        response.raise_for_status.return_value = None
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

    @patch("service.dify_service.KnowledgeBaseClient")
    def test_upload_text_sets_dataset_and_official_process_rule(self, client_class):
        """上传文本时应设置 dataset_id，并使用 schema 友好的分段规则。"""
        client = client_class.return_value
        client.list_datasets.return_value = self._response(
            {
                "data": [{"id": "dataset-id", "name": "app_schema"}],
                "has_more": False,
            }
        )
        client.create_document_by_text.return_value = self._response(
            {"document": {"id": "doc-id"}}
        )
        uploader = self._create_uploader()

        uploader.upload_text("app_schema", "# Table: users")

        self.assertEqual(client.dataset_id, "dataset-id")
        client.create_document_by_text.assert_called_once()
        _, kwargs = client.create_document_by_text.call_args
        self.assertEqual(kwargs["name"], "app_schema")
        self.assertEqual(kwargs["text"], "# Table: users")
        self.assertEqual(
            kwargs["extra_params"]["process_rule"]["rules"]["segmentation"],
            {"separator": "\n#", "max_tokens": 1000},
        )
        self.assertEqual(
            kwargs["extra_params"]["process_rule"]["mode"],
            "custom",
        )

    @patch("service.dify_service.KnowledgeBaseClient")
    def test_upload_file_skips_missing_or_empty_file(self, client_class):
        """文件不存在或为空时应跳过上传，不创建知识库文档。"""
        uploader = self._create_uploader()

        with tempfile.NamedTemporaryFile() as tmp_file:
            uploader.upload_file(tmp_file.name)

        client = client_class.return_value
        client.create_document_by_file.assert_not_called()
        client.create_dataset.assert_not_called()

    @patch("service.dify_service.KnowledgeBaseClient")
    def test_upload_file_sets_dataset_and_file_process_rule(self, client_class):
        """上传文件时应使用空行分段规则并设置 dataset_id。"""
        client = client_class.return_value
        client.list_datasets.return_value = self._response(
            {
                "data": [{"id": "dataset-id", "name": "schema"}],
                "has_more": False,
            }
        )
        client.create_document_by_file.return_value = self._response(
            {"document": {"id": "doc-id"}}
        )
        uploader = self._create_uploader()

        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = os.path.join(tmp_dir, "schema.md")
            with open(file_path, "w", encoding="utf-8") as file:
                file.write("# Table: users\n")

            uploader.upload_file(file_path)

        self.assertEqual(client.dataset_id, "dataset-id")
        client.create_document_by_file.assert_called_once()
        _, kwargs = client.create_document_by_file.call_args
        self.assertEqual(kwargs["file_path"], file_path)
        self.assertEqual(
            kwargs["extra_params"]["process_rule"]["rules"]["segmentation"],
            {"separator": "\n\n", "max_tokens": 1000},
        )


if __name__ == "__main__":
    unittest.main()
