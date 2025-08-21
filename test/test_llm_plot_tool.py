"""
测试修改后的 LLM 绘图工具
模拟 Dify 环境进行测试
"""

import sys
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def create_mock_session():
    """创建模拟的 Dify session"""
    mock_session = Mock()
    mock_model = Mock()
    mock_llm = Mock()
    
    # 模拟 LLM 响应
    def mock_invoke(model_config, prompt_messages, stream=False):
        # 根据 prompt 内容返回合适的配置
        user_message = prompt_messages[-1].content if prompt_messages else ""
        
        if "销售额" in user_message or "sales" in user_message.lower():
            response_content = json.dumps({
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
            response_content = json.dumps({
                "chart_type": "line",
                "title": "数据趋势图",
                "x_axis": {
                    "label": "时间",
                    "data": ["1月", "2月", "3月", "4月"]
                },
                "line_series": [
                    {
                        "label": "数据A",
                        "data": [10, 15, 12, 18]
                    }
                ]
            }, ensure_ascii=False)
        
        mock_response = Mock()
        mock_response.message = Mock()
        mock_response.message.content = response_content
        return mock_response
    
    mock_llm.invoke = mock_invoke
    mock_model.llm = mock_llm
    mock_session.model = mock_model
    
    return mock_session

def create_mock_runtime():
    """创建模拟的运行时环境"""
    mock_runtime = Mock()
    mock_credentials = {
        "output_dir": "output/test_charts"
    }
    mock_runtime.credentials = mock_credentials
    return mock_runtime

def test_llm_plot_tool():
    """测试 LLM 绘图工具"""
    print("🧪 测试 LLM 绘图工具...")
    
    # 确保输出目录存在
    output_dir = Path("output/test_charts")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # 导入工具类
        from tools.llm_plot import LLMPlotTool
        
        # 创建工具实例
        tool = LLMPlotTool()
        
        # 设置模拟环境
        tool.session = create_mock_session()
        tool.runtime = create_mock_runtime()
        tool._validate_config()
        
        print("✅ 工具初始化成功")
        
        # 测试数据1: 销售数据
        print("\n📊 测试1: 销售数据图表生成")
        test_data_1 = [
            {"quarter": "Q1", "sales": 150},
            {"quarter": "Q2", "sales": 180},
            {"quarter": "Q3", "sales": 165},
            {"quarter": "Q4", "sales": 200}
        ]
        
        tool_params_1 = {
            "user_question": "请显示最近四个季度的销售额变化",
            "data": json.dumps(test_data_1, ensure_ascii=False),
            "llm": {"model": "test-model"},
            "context": "这是季度销售报告",
            "use_simple": False
        }
        
        print("📋 调用工具...")
        result_generator = tool._invoke(tool_params_1)
        messages = list(result_generator)
        
        print(f"📝 收到 {len(messages)} 条消息:")
        for i, msg in enumerate(messages, 1):
            print(f"  {i}. {msg.message}")
        
        # 测试数据2: 简单数据
        print("\n📈 测试2: 简单趋势数据")
        test_data_2 = [
            {"month": "1月", "value": 100},
            {"month": "2月", "value": 120},
            {"month": "3月", "value": 110}
        ]
        
        tool_params_2 = {
            "user_question": "显示月度趋势",
            "data": json.dumps(test_data_2, ensure_ascii=False),
            "llm": {"model": "test-model"},
            "use_simple": True
        }
        
        print("📋 调用工具...")
        result_generator_2 = tool._invoke(tool_params_2)
        messages_2 = list(result_generator_2)
        
        print(f"📝 收到 {len(messages_2)} 条消息:")
        for i, msg in enumerate(messages_2, 1):
            print(f"  {i}. {msg.message}")
        
        print("\n✅ 测试完成！")
        print(f"📁 生成的图表保存在: {output_dir.absolute()}")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

def test_parameter_validation():
    """测试参数验证"""
    print("\n🔍 测试参数验证...")
    
    try:
        from tools.llm_plot import LLMPlotTool
        
        tool = LLMPlotTool()
        tool.runtime = create_mock_runtime()
        tool._validate_config()
        
        # 测试无效参数
        invalid_params = [
            {},  # 缺少必要参数
            {"user_question": ""},  # 空问题
            {"user_question": "test", "data": ""},  # 空数据
            {"user_question": "test", "data": "test"},  # 缺少 LLM
        ]
        
        for i, params in enumerate(invalid_params, 1):
            result = tool._validate_and_extract_parameters(params)
            if isinstance(result, str):  # 错误消息
                print(f"✅ 测试 {i}: 正确捕获错误 - {result}")
            else:
                print(f"❌ 测试 {i}: 应该返回错误但返回了: {result}")
        
        # 测试有效参数
        valid_params = {
            "user_question": "生成图表",
            "data": '{"test": "data"}',
            "llm": {"model": "test"},
            "context": "测试上下文",
            "use_simple": True
        }
        
        result = tool._validate_and_extract_parameters(valid_params)
        if isinstance(result, tuple):
            print(f"✅ 有效参数测试通过: {len(result)} 个参数")
        else:
            print(f"❌ 有效参数测试失败: {result}")
            
    except Exception as e:
        print(f"❌ 参数验证测试失败: {str(e)}")

if __name__ == "__main__":
    print("🚀 开始测试 LLM 绘图工具")
    print("=" * 50)
    
    test_parameter_validation()
    test_llm_plot_tool()
    
    print("\n" + "=" * 50)
    print("🎉 测试完成！")
