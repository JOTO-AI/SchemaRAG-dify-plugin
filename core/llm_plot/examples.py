"""
LLM 智能绘图模块使用示例
演示如何使用各种功能
"""

import json
from pathlib import Path
import sys

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.llm_plot import (
    initialize_chart_service,
    generate_smart_chart,
    generate_chart,
    validate_chart_config,
    get_chart_template,
    SUPPORTED_CHART_TYPES
)


def example_direct_chart_generation():
    """示例1：直接使用配置生成图表"""
    print("=== 示例1：直接生成柱状图 ===")
    
    # 柱状图配置
    bar_config = {
        "chart_type": "bar",
        "title": "2025年第一季度销售额统计",
        "x_axis": {
            "label": "月份",
            "data": ["2025-01", "2025-02", "2025-03"]
        },
        "y_axis": {
            "label": "销售额 (万元)",
            "data": [120, 135, 98]
        }
    }
    
    try:
        chart_path = generate_chart(bar_config)
        print(f"柱状图生成成功: {chart_path}")
    except Exception as e:
        print(f"生成失败: {e}")


def example_line_chart():
    """示例2：多系列折线图"""
    print("\n=== 示例2：多系列折线图 ===")
    
    line_config = {
        "chart_type": "line",
        "title": "产品销售趋势对比",
        "x_axis": {
            "label": "月份",
            "data": ["2024-10", "2024-11", "2024-12", "2025-01"]
        },
        "line_series": [
            {
                "label": "产品A",
                "data": [85, 92, 78, 95]
            },
            {
                "label": "产品B",
                "data": [70, 75, 82, 88]
            }
        ]
    }
    
    try:
        chart_path = generate_chart(line_config)
        print(f"折线图生成成功: {chart_path}")
    except Exception as e:
        print(f"生成失败: {e}")


def example_pie_chart():
    """示例3：饼图"""
    print("\n=== 示例3：饼图 ===")
    
    pie_config = {
        "chart_type": "pie",
        "title": "市场份额分布",
        "pie_data": {
            "labels": ["我们公司", "竞争对手A", "竞争对手B", "其他"],
            "values": [35.5, 28.2, 22.1, 14.2]
        }
    }
    
    try:
        chart_path = generate_chart(pie_config)
        print(f"饼图生成成功: {chart_path}")
    except Exception as e:
        print(f"生成失败: {e}")


def example_mock_llm_generation():
    """示例4：模拟 LLM 图表生成（不使用真实 LLM）"""
    print("\n=== 示例4：模拟 LLM 智能生成 ===")
    
    # 模拟 LLM 客户端
    class MockLLMClient:
        def chat(self, prompt):
            # 根据 prompt 内容返回合适的配置
            if "销售额" in prompt or "sales" in prompt.lower():
                return json.dumps({
                    "chart_type": "bar",
                    "title": "销售额统计",
                    "x_axis": {
                        "label": "时间",
                        "data": ["Q1", "Q2", "Q3", "Q4"]
                    },
                    "y_axis": {
                        "label": "销售额 (万元)",
                        "data": [150, 180, 165, 200]
                    }
                }, ensure_ascii=False)
            else:
                return json.dumps({
                    "chart_type": "line",
                    "title": "数据趋势",
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
                }, ensure_ascii=False)
    
    # 初始化服务
    mock_client = MockLLMClient()
    initialize_chart_service(llm_client=mock_client)
    
    # 模拟用户问题和数据
    user_question = "请显示最近四个季度的销售额变化"
    query_data = [
        {"quarter": "Q1", "sales": 150},
        {"quarter": "Q2", "sales": 180},
        {"quarter": "Q3", "sales": 165},
        {"quarter": "Q4", "sales": 200}
    ]
    
    try:
        result = generate_smart_chart(user_question, query_data)
        
        if result["success"]:
            print(f"智能图表生成成功: {result['chart_path']}")
            print(f"使用的配置: {json.dumps(result['chart_config'], ensure_ascii=False, indent=2)}")
        else:
            print(f"生成失败: {result['error']}")
            if result.get("fallback_data"):
                print(f"降级方案: {result['fallback_data']}")
                
    except Exception as e:
        print(f"生成失败: {e}")


def example_validation():
    """示例5：配置验证"""
    print("\n=== 示例5：配置验证 ===")
    
    # 有效配置
    valid_config = {
        "chart_type": "bar",
        "title": "测试图表",
        "x_axis": {"label": "X轴", "data": ["A", "B", "C"]},
        "y_axis": {"label": "Y轴", "data": [1, 2, 3]}
    }
    
    try:
        validated = validate_chart_config(valid_config)
        print("✓ 配置验证通过")
    except Exception as e:
        print(f"✗ 配置验证失败: {e}")
    
    # 无效配置
    invalid_config = {
        "chart_type": "invalid_type",
        "title": "测试图表"
    }
    
    try:
        validated = validate_chart_config(invalid_config)
        print("✓ 配置验证通过")
    except Exception as e:
        print(f"✗ 配置验证失败: {e}")


def example_templates():
    """示例6：使用模板"""
    print("\n=== 示例6：模板使用 ===")
    
    print(f"支持的图表类型: {SUPPORTED_CHART_TYPES}")
    
    for chart_type in ["bar", "line", "pie"]:
        try:
            template = get_chart_template(chart_type)
            print(f"\n{chart_type.upper()}图模板:")
            print(json.dumps(template, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"获取模板失败: {e}")


def main():
    """运行所有示例"""
    print("LLM 智能绘图模块使用示例")
    print("=" * 50)
    
    # 确保输出目录存在
    output_dir = Path("output/charts")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        example_direct_chart_generation()
        example_line_chart()
        example_pie_chart()
        example_mock_llm_generation()
        example_validation()
        example_templates()
        
        print("\n" + "=" * 50)
        print("所有示例运行完成！")
        print(f"生成的图表保存在: {output_dir.absolute()}")
        
    except Exception as e:
        print(f"示例运行出错: {e}")


if __name__ == "__main__":
    main()
