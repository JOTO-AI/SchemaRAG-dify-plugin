#!/usr/bin/env python3
"""
测试 Dify API 客户端
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.dify.dify_client import DifyClient, KnowledgeBaseClient  # noqa: E402


class TestDifyClient(unittest.TestCase):
    """Dify API 客户端测试"""

    def _mock_response(self, status_code=200, body=None):
        """创建 HTTP 响应 Mock"""
        response = Mock()
        response.status_code = status_code
        response.json.return_value = body or {"ok": True}
        response.raise_for_status.return_value = None
        return response

    @patch("core.dify.dify_client.httpx.Client")
    def test_json_requests_ignore_environment_proxies(self, mock_client_class):
        """JSON 请求不读取环境代理配置，避免内网 Dify API 误走代理"""
        response = self._mock_response()
        client_instance = mock_client_class.return_value.__enter__.return_value
        client_instance.request.return_value = response

        client = DifyClient("dataset-key", "http://192.168.198.169/v1")
        result = client._send_request("GET", "/datasets")

        self.assertIs(result, response)
        mock_client_class.assert_called_once_with(timeout=30.0, trust_env=False)
        client_instance.request.assert_called_once()

    @patch("core.dify.dify_client.httpx.Client")
    def test_http_status_error_keeps_api_error_message(self, mock_client_class):
        """HTTP 状态错误保留 API 错误信息，不包装成未知错误"""
        response = self._mock_response(
            status_code=409,
            body={"message": "The dataset name already exists."},
        )
        response.text = ""
        client_instance = mock_client_class.return_value.__enter__.return_value
        client_instance.request.return_value = response

        client = DifyClient("dataset-key", "http://192.168.198.169/v1")

        with self.assertRaises(ValueError) as context:
            client._send_request("POST", "/datasets")

        self.assertEqual(
            str(context.exception),
            "API请求失败: HTTP 409 - The dataset name already exists.",
        )

    @patch("core.dify.dify_client.httpx.Client")
    def test_file_requests_ignore_environment_proxies(self, mock_client_class):
        """文件上传请求也不读取环境代理配置"""
        response = self._mock_response()
        client_instance = mock_client_class.return_value.__enter__.return_value
        client_instance.request.return_value = response

        client = DifyClient("dataset-key", "http://192.168.198.169/v1")
        result = client._send_request_with_files(
            "POST",
            "/datasets/dataset-id/document/create-by-file",
            {"data": "{}"},
            {"file": ("schema.txt", b"content", "text/plain")},
        )

        self.assertIs(result, response)
        mock_client_class.assert_called_once_with(timeout=30.0, trust_env=False)

    @patch.object(KnowledgeBaseClient, "_send_request")
    def test_create_document_by_text_uses_current_official_endpoint(
        self, send_request
    ):
        """从文本创建文档使用当前官方 create-by-text 路径"""
        client = KnowledgeBaseClient(
            "dataset-key",
            "http://192.168.198.169/v1",
            dataset_id="dataset-id",
        )

        client.create_document_by_text("schema", "content")

        send_request.assert_called_once()
        self.assertEqual(
            send_request.call_args.args[:2],
            ("POST", "/datasets/dataset-id/document/create-by-text"),
        )

    @patch.object(KnowledgeBaseClient, "_send_request_with_files")
    @patch("core.dify.dify_client.os.path.getsize", return_value=10)
    @patch("core.dify.dify_client.os.path.exists", return_value=True)
    @patch("builtins.open")
    def test_create_document_by_file_uses_current_official_endpoint(
        self,
        mock_open,
        exists,
        getsize,
        send_request_with_files,
    ):
        """从文件创建文档使用当前官方 create-by-file 路径"""
        mock_open.return_value.__enter__.return_value = Mock()
        client = KnowledgeBaseClient(
            "dataset-key",
            "http://192.168.198.169/v1",
            dataset_id="dataset-id",
        )

        client.create_document_by_file("/tmp/schema.txt")

        send_request_with_files.assert_called_once()
        self.assertEqual(
            send_request_with_files.call_args.args[:2],
            ("POST", "/datasets/dataset-id/document/create-by-file"),
        )


if __name__ == "__main__":
    unittest.main()
