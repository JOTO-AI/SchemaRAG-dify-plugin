"""
测试中文字体支持
该脚本用于测试图表中文字体显示功能
"""

import sys
import os
from pathlib import Path
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.llm_plot import generate_chart

def test_chinese_fonts():
    """测试中文字体支持"""
    logger.info("开始测试中文字体支持...")
    
    # 确保输出目录存在
    output_dir = Path("output/charts")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 测试1: 带有中文的柱状图
    logger.info("生成中文柱状图...")
    bar_config = {
        "chart_type": "bar",
        "title": "各地区销售业绩对比",
        "x_axis": {
            "label": "地区",
            "data": ["北京", "上海", "广州", "深圳", "杭州"]
        },
        "y_axis": {
            "label": "销售额（万元）",
            "data": [120, 150, 100, 130, 110]
        },
        "style": {
            "figure_size": [10, 6],
            "dpi": 100
        }
    }
    
    try:
        chart_path = generate_chart(bar_config, str(output_dir))
        logger.info(f"中文柱状图生成成功: {chart_path}")
        print(f"✅ 中文柱状图已生成: {chart_path}")
    except Exception as e:
        logger.error(f"中文柱状图生成失败: {str(e)}")
        print(f"❌ 中文柱状图生成失败: {str(e)}")
    
    # 测试2: 带有中文的饼图
    logger.info("生成中文饼图...")
    pie_config = {
        "chart_type": "pie",
        "title": "市场份额分布情况",
        "pie_data": {
            "labels": ["华为", "小米", "苹果", "三星", "其他品牌"],
            "values": [30, 25, 20, 15, 10]
        },
        "style": {
            "figure_size": [8, 8],
            "dpi": 100
        }
    }
    
    try:
        chart_path = generate_chart(pie_config, str(output_dir))
        logger.info(f"中文饼图生成成功: {chart_path}")
        print(f"✅ 中文饼图已生成: {chart_path}")
    except Exception as e:
        logger.error(f"中文饼图生成失败: {str(e)}")
        print(f"❌ 中文饼图生成失败: {str(e)}")
    
    # 测试3: 带有中文的折线图
    logger.info("生成中文折线图...")
    line_config = {
        "chart_type": "line",
        "title": "各季度产品销量趋势",
        "x_axis": {
            "label": "季度",
            "data": ["第一季度", "第二季度", "第三季度", "第四季度"]
        },
        "line_series": [
            {
                "label": "高端产品",
                "data": [150, 180, 210, 230]
            },
            {
                "label": "中端产品",
                "data": [250, 220, 280, 300]
            },
            {
                "label": "入门产品",
                "data": [350, 380, 330, 390]
            }
        ],
        "style": {
            "figure_size": [10, 6],
            "dpi": 100
        }
    }
    
    try:
        chart_path = generate_chart(line_config, str(output_dir))
        logger.info(f"中文折线图生成成功: {chart_path}")
        print(f"✅ 中文折线图已生成: {chart_path}")
    except Exception as e:
        logger.error(f"中文折线图生成失败: {str(e)}")
        print(f"❌ 中文折线图生成失败: {str(e)}")
    
    print("\n测试总结:")
    print("- 如果图表生成成功且中文字符显示正常，则表示修复成功")
    print("- 图表文件保存在:", output_dir.absolute())
    print("- 请检查生成的图表，确认中文是否正常显示")

if __name__ == "__main__":
    test_chinese_fonts()
