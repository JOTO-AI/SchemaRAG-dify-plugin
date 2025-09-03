"""
基本图表生成测试
测试图表生成器的基本功能
"""
import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent))

from core.llm_plot.chart_generator import ChartGenerator

def test_basic_bar_chart():
    """
    测试基本柱状图生成
    """
    print("\n🧪 测试基本柱状图生成")
    
    # 创建输出目录
    output_dir = Path("output/basic_test")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建图表生成器
    chart_gen = ChartGenerator(str(output_dir))
    
    # 基本柱状图配置
    config = {
        "chart_type": "bar",
        "title": "测试柱状图",
        "x_axis": {
            "label": "类别",
            "data": ["A", "B", "C", "D", "E"]
        },
        "y_axis": {
            "label": "数值",
            "data": [10, 15, 7, 12, 9]
        },
        "style": {
            "format": "png",
            "colors": ["#3498db"]
        },
        "description": "这是一个测试柱状图"
    }
    
    try:
        # 生成图表
        chart_path = chart_gen.generate_chart(config)
        print(f"✅ 成功生成柱状图: {chart_path}")
        return True
    except Exception as e:
        print(f"❌ 柱状图生成失败: {str(e)}")
        return False

def test_basic_pie_chart():
    """
    测试基本饼图生成
    """
    print("\n🧪 测试基本饼图生成")
    
    # 创建输出目录
    output_dir = Path("output/basic_test")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建图表生成器
    chart_gen = ChartGenerator(str(output_dir))
    
    # 基本饼图配置
    config = {
        "chart_type": "pie",
        "title": "测试饼图",
        "pie_data": {
            "labels": ["A", "B", "C", "D"],
            "values": [35, 25, 20, 15]
        },
        "style": {
            "format": "png",
            "high_contrast": True
        },
        "description": "这是一个测试饼图"
    }
    
    try:
        # 生成图表
        chart_path = chart_gen.generate_chart(config)
        print(f"✅ 成功生成饼图: {chart_path}")
        return True
    except Exception as e:
        print(f"❌ 饼图生成失败: {str(e)}")
        return False

def test_svg_output():
    """
    测试SVG输出格式
    """
    print("\n🧪 测试SVG输出格式")
    
    # 创建输出目录
    output_dir = Path("output/basic_test")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建图表生成器
    chart_gen = ChartGenerator(str(output_dir))
    
    # SVG格式折线图配置
    config = {
        "chart_type": "line",
        "title": "测试折线图 (SVG格式)",
        "x_axis": {
            "label": "时间",
            "data": ["Jan", "Feb", "Mar", "Apr", "May"]
        },
        "line_series": [
            {
                "label": "系列A",
                "data": [10, 15, 13, 17, 20]
            }
        ],
        "style": {
            "format": "svg",
            "grid": True,
            "grid_alpha": 0.6
        },
        "description": "这是一个测试折线图 (SVG格式)"
    }
    
    try:
        # 生成图表
        chart_path = chart_gen.generate_chart(config)
        print(f"✅ 成功生成SVG格式折线图: {chart_path}")
        return True
    except Exception as e:
        print(f"❌ SVG格式折线图生成失败: {str(e)}")
        return False

def run_tests():
    """运行所有测试"""
    print("=" * 50)
    print("📊 图表生成器基本功能测试")
    print("=" * 50)
    
    tests = [
        test_basic_bar_chart,
        test_basic_pie_chart,
        test_svg_output
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 50)
    success_count = results.count(True)
    total_count = len(results)
    print(f"📋 测试结果: {success_count}/{total_count} 成功")
    
    if success_count == total_count:
        print("✅ 所有测试通过!")
    else:
        print("❌ 有测试失败!")
    
    print(f"📁 测试图表保存在: {os.path.abspath('output/basic_test')}")

if __name__ == "__main__":
    run_tests()
