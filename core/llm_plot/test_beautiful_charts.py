"""
测试美化后的图表样式
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.llm_plot import generate_chart

def test_beautiful_charts():
    """测试美化后的图表"""
    
    # 确保输出目录存在
    output_dir = Path("output/charts")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("🎨 测试美化后的图表样式...")
    
    # 测试1: 现代化柱状图
    print("\n📊 生成美化柱状图...")
    bar_config = {
        "chart_type": "bar",
        "title": "2025年季度销售业绩对比",
        "x_axis": {
            "label": "季度",
            "data": ["Q1", "Q2", "Q3", "Q4"]
        },
        "y_axis": {
            "label": "销售额 (万元)",
            "data": [156, 189, 172, 203]
        }
    }
    
    try:
        chart_path = generate_chart(bar_config, str(output_dir))
        print(f"✅ 柱状图生成成功: {chart_path}")
    except Exception as e:
        print(f"❌ 柱状图生成失败: {e}")
    
    # 测试2: 现代化折线图
    print("\n📈 生成美化折线图...")
    line_config = {
        "chart_type": "line",
        "title": "产品销售趋势分析",
        "x_axis": {
            "label": "月份",
            "data": ["1月", "2月", "3月", "4月", "5月", "6月"]
        },
        "line_series": [
            {
                "label": "产品A",
                "data": [85, 92, 78, 95, 102, 88]
            },
            {
                "label": "产品B",
                "data": [70, 75, 82, 88, 85, 91]
            },
            {
                "label": "产品C",
                "data": [60, 68, 72, 75, 79, 83]
            }
        ]
    }
    
    try:
        chart_path = generate_chart(line_config, str(output_dir))
        print(f"✅ 折线图生成成功: {chart_path}")
    except Exception as e:
        print(f"❌ 折线图生成失败: {e}")
    
    # 测试3: 现代化饼图
    print("\n🥧 生成美化饼图...")
    pie_config = {
        "chart_type": "pie",
        "title": "市场份额分布",
        "pie_data": {
            "labels": ["公司A", "公司B", "公司C", "公司D", "其他"],
            "values": [35.2, 28.7, 15.8, 12.3, 8.0]
        }
    }
    
    try:
        chart_path = generate_chart(pie_config, str(output_dir))
        print(f"✅ 饼图生成成功: {chart_path}")
    except Exception as e:
        print(f"❌ 饼图生成失败: {e}")
    
    # 测试4: 现代化散点图
    print("\n🔵 生成美化散点图...")
    scatter_config = {
        "chart_type": "scatter",
        "title": "销售额与广告投入关系分析",
        "x_axis": {
            "label": "广告投入 (万元)",
            "data": [10, 15, 20, 25, 30, 35, 40, 45]
        },
        "y_axis": {
            "label": "销售额 (万元)",
            "data": [50, 65, 78, 85, 95, 105, 115, 125]
        }
    }
    
    try:
        chart_path = generate_chart(scatter_config, str(output_dir))
        print(f"✅ 散点图生成成功: {chart_path}")
    except Exception as e:
        print(f"❌ 散点图生成失败: {e}")
    
    print(f"\n🎉 测试完成！所有图表已保存到: {output_dir.absolute()}")
    print("\n🎨 美化特性包括:")
    print("   • 现代化配色方案")
    print("   • 优雅的字体和间距")
    print("   • 简洁的坐标轴样式")
    print("   • 精致的网格线")
    print("   • 白色边框和阴影效果")
    print("   • 改进的图例样式")

if __name__ == "__main__":
    test_beautiful_charts()
