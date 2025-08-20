#!/usr/bin/env python3
"""
测试自定义提示功能
"""
import sys
import os
import unittest

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from prompt.text2sql_prompt import _build_system_prompt


class TestCustomPrompts(unittest.TestCase):
    """测试自定义提示功能"""

    def test_build_system_prompt_without_custom(self):
        """测试不带自定义提示的系统提示构建"""
        dialect = "mysql"
        db_schema = "CREATE TABLE users (id INT, name VARCHAR(50));"
        question = "How many users are there?"
        
        prompt = _build_system_prompt(dialect, db_schema, question)
        
        # 验证基础内容存在
        self.assertIn("mysql", prompt)
        self.assertIn("users", prompt)
        self.assertIn("Critical Requirements", prompt)

    def test_build_system_prompt_with_custom(self):
        """测试带自定义提示的系统提示构建"""
        dialect = "mysql"
        db_schema = "CREATE TABLE users (id INT, name VARCHAR(50));"
        question = "How many users are there?"
        custom_prompt = "Always use explicit column names and avoid SELECT *"
        
        prompt = _build_system_prompt(dialect, db_schema, question, custom_prompt)
        
        # 验证基础内容存在
        self.assertIn("mysql", prompt)
        self.assertIn("users", prompt)
        self.assertIn("Critical Requirements", prompt)
        # 验证自定义提示存在
        self.assertIn("Custom Instructions", prompt)
        self.assertIn("Always use explicit column names", prompt)

    def test_build_system_prompt_empty_custom(self):
        """测试空自定义提示的处理"""
        dialect = "mysql"
        db_schema = "CREATE TABLE users (id INT, name VARCHAR(50));"
        question = "How many users are there?"
        custom_prompt = ""
        
        prompt = _build_system_prompt(dialect, db_schema, question, custom_prompt)
        
        # 验证基础内容存在，但没有自定义部分
        self.assertIn("mysql", prompt)
        self.assertIn("users", prompt)
        self.assertIn("Critical Requirements", prompt)
        self.assertNotIn("Custom Instructions", prompt)


if __name__ == "__main__":
    unittest.main()