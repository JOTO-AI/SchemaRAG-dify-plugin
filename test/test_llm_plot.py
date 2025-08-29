"""
LLM 绘图工具测试和演示
"""

import json
import sys
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent.parent))

from tools.llm_plot import llm_plot, initialize_llm_plot_tool


class MockLLMClient:
    """模拟 LLM 客户端，用于测试"""
    
    def chat(self, prompt):
        """模拟 LLM 聊天响应"""
        # 根据 prompt 内容智能返回合适的配置
        prompt_lower = prompt.lower()
        
        if "销售" in prompt or "sales" in prompt_lower:
            if "趋势" in prompt or "trend" in prompt_lower or "变化" in prompt:
                # 折线图适合趋势
                return json.dumps({
                    "chart_type": "line",
                    "title": "销售趋势分析",
                    "x_axis": {
                        "label": "时间",
                        "data": ["Q1", "Q2", "Q3", "Q4"]
                    },
                    "line_series": [
                        {
                            "label": "销售额",
                            "data": [150, 180, 165, 200]
                        }
                    ]
                }, ensure_ascii=False)
            else:
                # 柱状图适合比较
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
        
        elif "份额" in prompt or "比例" in prompt or "share" in prompt_lower:
            # 饼图适合份额展示
            return json.dumps({
                "chart_type": "pie",
                "title": "市场份额分布",
                "pie_data": {
                    "labels": ["公司A", "公司B", "公司C", "其他"],
                    "values": [35.2, 28.7, 22.1, 14.0]
                }
            }, ensure_ascii=False)
        
        elif "相关" in prompt or "关系" in prompt or "correlation" in prompt_lower:
            # 散点图适合相关性
            return json.dumps({
                "chart_type": "scatter",
                "title": "数据相关性分析",
                "x_axis": {
                    "label": "X轴数据",
                    "data": [10, 20, 30, 40, 50]
                },
                "y_axis": {
                    "label": "Y轴数据",
                    "data": [15, 25, 35, 45, 55]
                }
            }, ensure_ascii=False)
        
        else:
            # 默认柱状图
            return json.dumps({
                "chart_type": "bar",
                "title": "数据统计图表",
                "x_axis": {
                    "label": "类别",
                    "data": ["A", "B", "C", "D"]
                },
                "y_axis": {
                    "label": "数值",
                    "data": [10, 20, 15, 25]
                }
            }, ensure_ascii=False)


def test_basic_functionality():
    """测试基本功能"""
    print("🧪 测试 LLM 绘图工具基本功能")
    print("=" * 50)
    
    # 初始化工具
    mock_client = MockLLMClient()
    initialize_llm_plot_tool(mock_client, "output/test_charts")
    
    # 测试用例
    test_cases = [
        {
            "name": "销售趋势分析",
            "question": "请显示最近四个季度的销售额趋势变化",
            "data": json.dumps([
                {"quarter": "Q1", "sales": 150},
                {"quarter": "Q2", "sales": 180},
                {"quarter": "Q3", "sales": 165},
                {"quarter": "Q4", "sales": 200}
            ])
        },
        {
            "name": "市场份额分布",
            "question": "显示各公司的市场份额比例",
            "data": json.dumps([
                {"company": "公司A", "share": 35.2},
                {"company": "公司B", "share": 28.7},
                {"company": "公司C", "share": 22.1},
                {"company": "其他", "share": 14.0}
            ])
        },
        {
            "name": "部门销售对比",
            "question": "比较各部门的销售业绩",
            "data": json.dumps({
                "部门A": 120,
                "部门B": 135,
                "部门C": 98,
                "部门D": 156
            })
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📊 测试 {i}: {test_case['name']}")
        print(f"问题: {test_case['question']}")
        
        try:
            result = llm_plot(
                user_question=test_case['question'],
                data=test_case['data']
            )
            
            if result["success"]:
                print(f"✅ 成功生成 {result.get('chart_type', '未知')} 类型图表")
                print(f"   文件路径: {result.get('chart_path', 'N/A')}")
                print(f"   访问链接: {result.get('chart_url', 'N/A')}")
                print(f"   结果消息: {result.get('message', 'N/A')}")
            else:
                print(f"❌ 生成失败: {result.get('message', 'N/A')}")
                if result.get("fallback_data"):
                    print(f"   降级数据: {result['fallback_data']}")
                    
        except Exception as e:
            print(f"❌ 测试异常: {str(e)}")


def test_dify_integration():
    """测试 Dify 集成示例"""
    print("\n🔧 Dify 集成使用示例")
    print("=" * 30)
    
    # 模拟 Dify 工作流中的调用
    workflow_data = {
        "user_input": "显示公司各季度收入情况",
        "sql_result": [
            {"quarter": "2024Q1", "revenue": 1200000},
            {"quarter": "2024Q2", "revenue": 1350000},
            {"quarter": "2024Q3", "revenue": 1180000},
            {"quarter": "2024Q4", "revenue": 1520000}
        ]
    }
    
    print("Dify 工作流输入:")
    print(f"用户问题: {workflow_data['user_input']}")
    print(f"SQL 查询结果: {json.dumps(workflow_data['sql_result'], indent=2, ensure_ascii=False)}")
    
    # 调用 LLM 绘图工具
    result = llm_plot(
        user_question=workflow_data['user_input'],
        data=json.dumps(workflow_data['sql_result']),
        context="这是公司财务数据，需要生成清晰的收入趋势图"
    )
    
    print("\nLLM 绘图工具输出:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 模拟返回给 Dify 的结果
    dify_response = {
        "chart_generated": result["success"],
        "chart_url": result.get("chart_url"),
        "chart_description": result.get("message"),
        "chart_type": result.get("chart_type")
    }
    
    print("\n返回给 Dify 的响应:")
    print(json.dumps(dify_response, indent=2, ensure_ascii=False))


def test_error_handling():
    """测试错误处理"""
    print("\n🚨 错误处理测试")
    print("=" * 20)
    
    # 测试无效数据
    print("测试无效数据:")
    result = llm_plot(
        user_question="生成图表",
        data="这不是有效的数据格式"
    )
    print(f"结果: {result.get('message', 'N/A')}")
    
    # 测试空数据
    print("\n测试空数据:")
    result = llm_plot(
        user_question="显示数据",
        data=""
    )
    print(f"结果: {result.get('message', 'N/A')}")


def main():
    """运行所有测试"""
    print("🎨 LLM 智能绘图工具测试套件")
    print("=" * 60)
    
    # 确保输出目录存在
    output_dir = Path("output/test_charts")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        test_basic_functionality()
        test_dify_integration()
        test_error_handling()
        
        print("\n" + "=" * 60)
        print("🎉 所有测试完成！")
        print(f"生成的测试图表保存在: {output_dir.absolute()}")
        
        print("\n📋 使用说明:")
        print("1. 在 Dify 工作流中添加自定义工具")
        print("2. 工具配置指向 tools/llm_plot.yaml")
        print("3. 传入用户问题和数据即可生成图表")
        print("4. 工具会返回图表路径和访问 URL")
        
    except Exception as e:
        print(f"❌ 测试运行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
