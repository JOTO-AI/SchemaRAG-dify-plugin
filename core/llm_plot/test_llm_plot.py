"""
LLM 智能绘图模块单元测试
"""

import unittest
import json
import tempfile
import shutil
from pathlib import Path
import sys

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.llm_plot import (
    ChartConfig,
    ChartGenerator,
    LLMChartController,
    validate_chart_config,
    get_chart_template,
    create_chart_prompt,
    SUPPORTED_CHART_TYPES
)


class TestChartSchema(unittest.TestCase):
    """测试图表配置规范"""
    
    def test_valid_bar_config(self):
        """测试有效的柱状图配置"""
        config = {
            "chart_type": "bar",
            "title": "测试柱状图",
            "x_axis": {
                "label": "类别",
                "data": ["A", "B", "C"]
            },
            "y_axis": {
                "label": "数值",
                "data": [10, 20, 15]
            }
        }
        
        validated = validate_chart_config(config)
        self.assertEqual(validated.chart_type, "bar")
        self.assertEqual(validated.title, "测试柱状图")
    
    def test_valid_pie_config(self):
        """测试有效的饼图配置"""
        config = {
            "chart_type": "pie",
            "title": "测试饼图",
            "pie_data": {
                "labels": ["A", "B", "C"],
                "values": [30, 40, 30]
            }
        }
        
        validated = validate_chart_config(config)
        self.assertEqual(validated.chart_type, "pie")
        self.assertIsNotNone(validated.pie_data)
    
    def test_invalid_chart_type(self):
        """测试无效的图表类型"""
        config = {
            "chart_type": "invalid",
            "title": "测试"
        }
        
        with self.assertRaises(ValueError):
            validate_chart_config(config)
    
    def test_missing_required_fields(self):
        """测试缺少必需字段"""
        config = {
            "chart_type": "bar",
            "title": "测试"
            # 缺少 x_axis 和 y_axis
        }
        
        with self.assertRaises(ValueError):
            validate_chart_config(config)


class TestChartGenerator(unittest.TestCase):
    """测试图表生成器"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.generator = ChartGenerator(self.temp_dir)
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir)
    
    def test_generate_bar_chart(self):
        """测试生成柱状图"""
        config = {
            "chart_type": "bar",
            "title": "测试柱状图",
            "x_axis": {
                "label": "类别",
                "data": ["A", "B", "C"]
            },
            "y_axis": {
                "label": "数值",
                "data": [10, 20, 15]
            }
        }
        
        chart_path = self.generator.generate_chart(config)
        self.assertTrue(Path(chart_path).exists())
        self.assertTrue(chart_path.endswith('.png'))
    
    def test_generate_line_chart(self):
        """测试生成折线图"""
        config = {
            "chart_type": "line",
            "title": "测试折线图",
            "x_axis": {
                "label": "时间",
                "data": ["1月", "2月", "3月"]
            },
            "line_series": [
                {
                    "label": "数据A",
                    "data": [10, 15, 12]
                }
            ]
        }
        
        chart_path = self.generator.generate_chart(config)
        self.assertTrue(Path(chart_path).exists())
    
    def test_generate_pie_chart(self):
        """测试生成饼图"""
        config = {
            "chart_type": "pie",
            "title": "测试饼图",
            "pie_data": {
                "labels": ["A", "B", "C"],
                "values": [30, 40, 30]
            }
        }
        
        chart_path = self.generator.generate_chart(config)
        self.assertTrue(Path(chart_path).exists())


class TestPromptGeneration(unittest.TestCase):
    """测试 Prompt 生成"""
    
    def test_create_prompt(self):
        """测试创建 Prompt"""
        user_question = "显示销售数据"
        query_data = [{"month": "1月", "sales": 100}]
        
        prompt = create_chart_prompt(user_question, query_data)
        
        self.assertIn("销售数据", prompt)
        self.assertIn("1月", prompt)
        self.assertIn("chart_type", prompt)
    
    def test_simple_prompt(self):
        """测试简化 Prompt"""
        user_question = "显示趋势"
        query_data = {"data": [1, 2, 3]}
        
        prompt = create_chart_prompt(user_question, query_data, use_simple=True)
        
        self.assertIn("趋势", prompt)
        self.assertTrue(len(prompt) < 2000)  # 简化版应该更短


class TestLLMController(unittest.TestCase):
    """测试 LLM 控制器"""
    
    def setUp(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        
        # 模拟 LLM 客户端
        class MockLLMClient:
            def chat(self, prompt):
                return json.dumps({
                    "chart_type": "bar",
                    "title": "测试图表",
                    "x_axis": {
                        "label": "类别",
                        "data": ["A", "B"]
                    },
                    "y_axis": {
                        "label": "数值",
                        "data": [10, 20]
                    }
                })
        
        self.controller = LLMChartController(
            llm_client=MockLLMClient(),
            output_dir=self.temp_dir
        )
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.temp_dir)
    
    def test_generate_chart_from_data(self):
        """测试从数据生成图表"""
        user_question = "显示数据"
        query_data = [{"category": "A", "value": 10}]
        
        result = self.controller.generate_chart_from_data(user_question, query_data)
        
        self.assertTrue(result["success"])
        self.assertIsNotNone(result["chart_path"])
        self.assertTrue(Path(result["chart_path"]).exists())
    
    def test_generate_chart_from_config(self):
        """测试从配置生成图表"""
        config = {
            "chart_type": "bar",
            "title": "直接配置图表",
            "x_axis": {
                "label": "类别",
                "data": ["X", "Y"]
            },
            "y_axis": {
                "label": "数值",
                "data": [5, 8]
            }
        }
        
        result = self.controller.generate_chart_from_config(config)
        
        self.assertTrue(result["success"])
        self.assertIsNotNone(result["chart_path"])


class TestUtilityFunctions(unittest.TestCase):
    """测试工具函数"""
    
    def test_supported_chart_types(self):
        """测试支持的图表类型"""
        self.assertIn("bar", SUPPORTED_CHART_TYPES)
        self.assertIn("line", SUPPORTED_CHART_TYPES)
        self.assertIn("pie", SUPPORTED_CHART_TYPES)
    
    def test_get_chart_template(self):
        """测试获取图表模板"""
        template = get_chart_template("bar")
        
        self.assertEqual(template["chart_type"], "bar")
        self.assertIn("title", template)
        self.assertIn("x_axis", template)
        self.assertIn("y_axis", template)
    
    def test_invalid_template_type(self):
        """测试无效的模板类型"""
        with self.assertRaises(ValueError):
            get_chart_template("invalid_type")


if __name__ == "__main__":
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestChartSchema))
    suite.addTests(loader.loadTestsFromTestCase(TestChartGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestPromptGeneration))
    suite.addTests(loader.loadTestsFromTestCase(TestLLMController))
    suite.addTests(loader.loadTestsFromTestCase(TestUtilityFunctions))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出结果
    if result.wasSuccessful():
        print("\n✓ 所有测试通过！")
    else:
        print(f"\n✗ 测试失败: {len(result.failures)} 个失败, {len(result.errors)} 个错误")
