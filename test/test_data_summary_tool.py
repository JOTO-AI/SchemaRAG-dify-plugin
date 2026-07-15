"""
测试数据摘要工具的输入处理与 LLM 调用编排。
"""

from types import SimpleNamespace

import pytest

from service.plugin_logging import get_plugin_logger
from tools.data_summary import DataSummaryTool


def _create_tool() -> DataSummaryTool:
    """创建不依赖 Dify runtime 的工具实例。"""
    tool = object.__new__(DataSummaryTool)
    tool.logger = get_plugin_logger("test.data_summary_tool")
    tool.create_text_message = lambda text=None, **kwargs: text or kwargs.get("text")
    return tool


def _chunk(content: str):
    """创建流式 LLM chunk 替身。"""
    return SimpleNamespace(
        delta=SimpleNamespace(
            message=SimpleNamespace(content=content),
        )
    )


def test_data_summary_validates_input_and_formats_json():
    """输入校验和 JSON 格式化应独立可测。"""
    tool = _create_tool()

    assert tool._validate_input_data("{}", "分析") == (True, "")
    assert tool._validate_input_data("", "分析")[1] == "数据内容不能为空"
    assert tool._validate_input_data("{}", "")[1] == "分析查询不能为空"
    assert tool._validate_input_data("x", "q", "r" * 2001)[1] == (
        "自定义规则过长，最大支持 2000 字符"
    )

    formatted = tool._format_data_content('{"name":"张三","score":95}', "auto")
    assert '"name": "张三"' in formatted
    assert '"score": 95' in formatted

    assert tool._format_data_content("  plain text  ", "auto") == "plain text"


def test_data_summary_truncates_long_data_with_notice():
    """长数据应截断并带提示，避免超长 prompt。"""
    tool = _create_tool()

    truncated, was_truncated = tool._truncate_data_if_needed("x" * 120, max_length=110)

    assert was_truncated is True
    assert len(truncated) <= 120
    assert "数据内容过长已被截断" in truncated


def test_data_summary_invoke_uses_custom_prompt_and_streams_chunks():
    """自定义 prompt 应替换变量，并按 LLM 流式 chunk 输出。"""
    tool = _create_tool()
    calls = {}

    class FakeLLM:
        def invoke(self, **kwargs):
            calls.update(kwargs)
            return [_chunk("结论"), _chunk("：稳定")]

    tool.session = SimpleNamespace(
        model=SimpleNamespace(
            llm=FakeLLM(),
        )
    )

    outputs = list(
        tool._invoke(
            {
                "data_content": '{"metric":"ARR","value":123}',
                "query": "总结指标",
                "llm": {"provider": "fake"},
                "user_prompt": "请分析 {{data}} / {{query}}",
            }
        )
    )

    assert outputs == ["结论", "：稳定"]
    assert calls["model_config"] == {"provider": "fake"}
    assert calls["stream"] is True
    user_prompt = calls["prompt_messages"][1].content
    assert '"metric": "ARR"' in user_prompt
    assert "总结指标" in user_prompt


def test_data_summary_invoke_wraps_validation_errors():
    """缺少 LLM 配置时应返回工具级可读错误。"""
    tool = _create_tool()

    with pytest.raises(ValueError, match="数据摘要工具执行失败: 缺少LLM模型配置"):
        list(
            tool._invoke(
                {
                    "data_content": "[]",
                    "query": "分析",
                }
            )
        )
