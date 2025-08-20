#!/usr/bin/env python3
"""
综合测试所有新功能
"""
import sys
import os
import unittest

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from prompt.text2sql_prompt import _build_system_prompt


class TestIntegratedFeatures(unittest.TestCase):
    """测试集成功能"""

    def test_comprehensive_prompt_building(self):
        """测试完整的提示构建流程"""
        dialect = "mysql"
        db_schema = """
=== 来自数据集 dataset_users 的架构信息 ===
CREATE TABLE users (
    id INT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE
);

=== 来自数据集 dataset_orders 的架构信息 ===
CREATE TABLE orders (
    id INT PRIMARY KEY,
    user_id INT,
    total_amount DECIMAL(10,2),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
        """
        question = "Show me total sales per user"
        custom_prompt = "Always use explicit JOIN syntax and include user email in results"
        
        prompt = _build_system_prompt(dialect, db_schema, question, custom_prompt)
        
        # 验证基础组件
        self.assertIn("mysql", prompt)
        self.assertIn("Database Schema", prompt)
        
        # 验证多数据集内容
        self.assertIn("dataset_users", prompt)
        self.assertIn("dataset_orders", prompt)
        self.assertIn("users", prompt)
        self.assertIn("orders", prompt)
        
        # 验证自定义提示
        self.assertIn("Custom Instructions", prompt)
        self.assertIn("explicit JOIN syntax", prompt)
        self.assertIn("user email", prompt)
        
        # 验证基础结构完整性
        self.assertIn("Critical Requirements", prompt)
        self.assertIn("Schema Adherence", prompt)
        self.assertIn("Output Format", prompt)

    def test_multiple_dataset_string_processing(self):
        """测试多数据集字符串处理"""
        # 测试各种输入格式
        test_cases = [
            ("dataset1,dataset2,dataset3", ["dataset1", "dataset2", "dataset3"]),
            ("dataset1, dataset2, dataset3", ["dataset1", "dataset2", "dataset3"]),
            (" dataset1 , dataset2 , dataset3 ", ["dataset1", "dataset2", "dataset3"]),
            ("dataset1", ["dataset1"]),
            ("", []),
            ("dataset1,,dataset2", ["dataset1", "dataset2"]),
        ]
        
        for input_str, expected in test_cases:
            with self.subTest(input_str=input_str):
                parsed = [id.strip() for id in input_str.split(",") if id.strip()]
                self.assertEqual(parsed, expected)

    def test_database_config_priority(self):
        """测试数据库配置优先级逻辑"""
        # 模拟provider配置
        provider_config = {
            "db_type": "mysql",
            "db_host": "localhost",
            "db_port": 3306,
            "db_user": "root",
            "db_password": "password",
            "db_name": "testdb"
        }
        
        # 模拟工具参数（部分覆盖）
        tool_params = {
            "db_host": "prod.example.com",
            "db_port": "5432",
            "db_name": "production_db"
        }
        
        # 模拟有效配置逻辑
        effective_config = {}
        for key, provider_value in provider_config.items():
            param_key = key
            if param_key == "db_port":
                # 处理端口号转换
                tool_value = tool_params.get(param_key)
                if tool_value:
                    effective_config[key] = int(tool_value)
                else:
                    effective_config[key] = provider_value
            else:
                effective_config[key] = tool_params.get(param_key, provider_value)
        
        # 验证优先级正确
        self.assertEqual(effective_config["db_type"], "mysql")  # 使用provider配置
        self.assertEqual(effective_config["db_host"], "prod.example.com")  # 使用工具参数
        self.assertEqual(effective_config["db_port"], 5432)  # 使用工具参数，转换为整数
        self.assertEqual(effective_config["db_user"], "root")  # 使用provider配置
        self.assertEqual(effective_config["db_name"], "production_db")  # 使用工具参数

    def test_backward_compatibility(self):
        """测试向后兼容性"""
        # 测试不提供新参数的情况
        dialect = "mysql"
        db_schema = "CREATE TABLE users (id INT, name VARCHAR(50));"
        question = "How many users are there?"
        
        # 不提供自定义提示
        prompt_without_custom = _build_system_prompt(dialect, db_schema, question)
        self.assertNotIn("Custom Instructions", prompt_without_custom)
        
        # 提供空自定义提示
        prompt_with_empty_custom = _build_system_prompt(dialect, db_schema, question, "")
        self.assertNotIn("Custom Instructions", prompt_with_empty_custom)
        
        # 提供None作为自定义提示
        prompt_with_none_custom = _build_system_prompt(dialect, db_schema, question, None)
        self.assertNotIn("Custom Instructions", prompt_with_none_custom)


if __name__ == "__main__":
    unittest.main()