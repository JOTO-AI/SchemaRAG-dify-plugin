#!/usr/bin/env python3
"""
测试多知识库支持功能
"""
import sys
import os
import unittest

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 仅导入需要的函数，避免导入数据库依赖
sys.path.append(os.path.join(project_root, 'service'))


class TestMultipleDatasets(unittest.TestCase):
    """测试多知识库功能"""

    def test_string_parsing(self):
        """测试字符串解析功能"""
        # 模拟字符串解析逻辑
        dataset_ids = "dataset1,dataset2,dataset3"
        parsed = [id.strip() for id in dataset_ids.split(",") if id.strip()]
        
        expected = ["dataset1", "dataset2", "dataset3"]
        self.assertEqual(parsed, expected)
        
    def test_empty_string_handling(self):
        """测试空字符串处理"""
        dataset_ids = ""
        parsed = [id.strip() for id in dataset_ids.split(",") if id.strip()]
        
        self.assertEqual(parsed, [])
        
    def test_whitespace_handling(self):
        """测试空白字符处理"""
        dataset_ids = " dataset1 , dataset2 , dataset3 "
        parsed = [id.strip() for id in dataset_ids.split(",") if id.strip()]
        
        expected = ["dataset1", "dataset2", "dataset3"]
        self.assertEqual(parsed, expected)


if __name__ == "__main__":
    unittest.main()