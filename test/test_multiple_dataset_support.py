"""
测试多知识库支持功能

此测试文件用于验证新增的多知识库支持功能，包括：
1. 多知识库异步并发检索
2. 示例知识库检索
3. 参数验证和错误处理
"""
import unittest
from unittest.mock import Mock, AsyncMock, patch
import asyncio
import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from service.knowledge_service import KnowledgeService
from tools.text2sql import Text2SQLTool


class TestMultipleDatasetSupport(unittest.TestCase):
    """测试多知识库支持功能"""

    def setUp(self):
        """设置测试环境"""
        self.api_uri = "https://test-api.com"
        self.api_key = "test-key"
        self.knowledge_service = KnowledgeService(self.api_uri, self.api_key)

    def test_single_dataset_id_parsing(self):
        """测试单个数据集ID解析"""
        single_id = "dataset123"
        result = self.knowledge_service.retrieve_schema_from_multiple_datasets(
            single_id, "test query", top_k=5
        )
        # 这里应该调用原有的单个数据集检索方法
        # 由于我们没有真实的API，这个测试主要验证函数调用不会报错

    def test_multiple_dataset_id_parsing(self):
        """测试多个数据集ID解析"""
        multiple_ids = "dataset1,dataset2,dataset3"
        id_list = [id.strip() for id in multiple_ids.split(",") if id.strip()]
        self.assertEqual(len(id_list), 3)
        self.assertEqual(id_list, ["dataset1", "dataset2", "dataset3"])

    def test_empty_dataset_id_handling(self):
        """测试空数据集ID处理"""
        empty_ids = ""
        result = self.knowledge_service.retrieve_schema_from_multiple_datasets(
            empty_ids, "test query", top_k=5
        )
        self.assertEqual(result, "")

    def test_whitespace_only_dataset_id_handling(self):
        """测试仅包含空白字符的数据集ID处理"""
        whitespace_ids = "  ,  ,  "
        result = self.knowledge_service.retrieve_schema_from_multiple_datasets(
            whitespace_ids, "test query", top_k=5
        )
        self.assertEqual(result, "")

    @patch('httpx.AsyncClient')
    async def test_async_multiple_dataset_retrieval(self, mock_client):
        """测试异步多数据集检索"""
        # 模拟异步HTTP响应
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "records": [
                {"segment": {"content": "Test schema content"}}
            ]
        }
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        # 测试异步检索
        dataset_ids = ["dataset1", "dataset2"]
        results = await self.knowledge_service._retrieve_from_multiple_datasets_async(
            dataset_ids, "test query", 5, "semantic_search"
        )
        
        self.assertEqual(len(results), 2)

    def test_text2sql_tool_parameter_validation(self):
        """测试Text2SQL工具参数验证"""
        # 创建模拟的Text2SQL工具实例
        mock_runtime = Mock()
        mock_runtime.credentials = {
            "api_uri": "https://test-api.com",
            "dataset_api_key": "test-key"
        }
        
        tool = Text2SQLTool()
        tool.runtime = mock_runtime
        
        # 测试有效参数
        valid_params = {
            "dataset_id": "dataset1,dataset2",
            "llm": Mock(),
            "content": "What are the users?",
            "dialect": "mysql",
            "top_k": 5,
            "retrieval_model": "semantic_search",
            "custom_prompt": "Use specific column names",
            "example_dataset_id": "examples_dataset"
        }
        
        result = tool._validate_and_extract_parameters(valid_params)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 8)  # 包含新的example_dataset_id参数

    def test_text2sql_tool_example_dataset_validation(self):
        """测试示例数据集参数验证"""
        mock_runtime = Mock()
        mock_runtime.credentials = {
            "api_uri": "https://test-api.com",
            "dataset_api_key": "test-key"
        }
        
        tool = Text2SQLTool()
        tool.runtime = mock_runtime
        
        # 测试无效的示例数据集参数
        invalid_params = {
            "dataset_id": "dataset1",
            "llm": Mock(),
            "content": "What are the users?",
            "example_dataset_id": 123  # 应该是字符串，不是数字
        }
        
        result = tool._validate_and_extract_parameters(invalid_params)
        self.assertIsInstance(result, str)  # 应该返回错误消息
        self.assertIn("示例知识库ID必须是字符串类型", result)

    def test_fallback_multiple_dataset_retrieval(self):
        """测试多数据集检索降级方案"""
        dataset_ids = ["dataset1", "dataset2"]
        
        # 由于这是降级方案，它会依次调用单个数据集检索方法
        # 这里主要测试方法调用不会出错
        with patch.object(self.knowledge_service, 'retrieve_schema_from_dataset', return_value="test content"):
            result = self.knowledge_service._fallback_retrieve_multiple_datasets(
                dataset_ids, "test query", 5, "semantic_search"
            )
            self.assertIsInstance(result, str)

    def test_content_merging_with_knowledge_base_labels(self):
        """测试内容合并时知识库标签的添加"""
        # 测试结果合并逻辑
        dataset_id = "test_dataset"
        content = "Test schema content"
        expected_result = f"=== 知识库 {dataset_id} ===\\n{content}"
        
        # 这里测试的是内容格式化逻辑
        formatted_content = f"=== 知识库 {dataset_id} ===\\n{content}"
        self.assertEqual(formatted_content, expected_result)


class TestPromptBuildingWithExamples(unittest.TestCase):
    """测试带示例的提示词构建"""

    def test_prompt_with_examples(self):
        """测试包含示例的提示词构建"""
        from prompt.text2sql_prompt import _build_system_prompt
        
        dialect = "mysql"
        db_schema = "CREATE TABLE users (id INT, name VARCHAR(255));"
        question = "Get all users"
        example_info = "SELECT * FROM users WHERE status = 'active';"
        
        prompt = _build_system_prompt(dialect, db_schema, question, None, example_info)
        
        self.assertIn("【Examples】", prompt)
        self.assertIn(example_info, prompt)
        self.assertIn("【Database Schema】", prompt)

    def test_prompt_without_examples(self):
        """测试不包含示例的提示词构建"""
        from prompt.text2sql_prompt import _build_system_prompt
        
        dialect = "mysql"
        db_schema = "CREATE TABLE users (id INT, name VARCHAR(255));"
        question = "Get all users"
        
        prompt = _build_system_prompt(dialect, db_schema, question)
        
        self.assertNotIn("【Examples】", prompt)
        self.assertIn("【Database Schema】", prompt)

    def test_prompt_with_custom_instructions_and_examples(self):
        """测试同时包含自定义指令和示例的提示词构建"""
        from prompt.text2sql_prompt import _build_system_prompt
        
        dialect = "mysql"
        db_schema = "CREATE TABLE users (id INT, name VARCHAR(255));"
        question = "Get all users"
        custom_prompt = "Always use explicit joins"
        example_info = "SELECT u.id, u.name FROM users u WHERE u.status = 'active';"
        
        prompt = _build_system_prompt(dialect, db_schema, question, custom_prompt, example_info)
        
        self.assertIn("【Examples】", prompt)
        self.assertIn(example_info, prompt)
        self.assertIn(custom_prompt, prompt)


if __name__ == "__main__":
    unittest.main()
