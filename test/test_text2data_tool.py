"""
测试 Text2Data 工具中可隔离的数据摘要输出逻辑。
"""

import json
import sys
from types import SimpleNamespace

for module_name in [
    "dify_plugin",
    "dify_plugin.config",
    "dify_plugin.config.logger_format",
    "dify_plugin.entities",
    "dify_plugin.entities.model",
    "dify_plugin.entities.model.message",
    "dify_plugin.entities.tool",
    "dify_plugin.errors",
    "dify_plugin.errors.tool",
    "service.plugin_logging",
]:
    sys.modules.pop(module_name, None)

from service.plugin_logging import get_plugin_logger  # noqa: E402
from tools.text2data import Text2DataTool  # noqa: E402


class FakeDatabaseService:
    """格式化输出替身。"""

    def _format_output(self, results, columns, output_format):
        assert output_format == "json"
        return json.dumps(results, ensure_ascii=False)


def _chunk(content: str):
    """创建流式 LLM chunk 替身。"""
    return SimpleNamespace(
        delta=SimpleNamespace(
            message=SimpleNamespace(content=content),
        )
    )


def _create_tool(llm):
    """创建不依赖 Dify runtime 的 Text2DataTool 实例。"""
    tool = object.__new__(Text2DataTool)
    tool.logger = get_plugin_logger("test.text2data_tool")
    tool.db_service = FakeDatabaseService()
    tool.session = SimpleNamespace(
        model=SimpleNamespace(
            llm=llm,
        )
    )
    tool.create_text_message = lambda text=None, **kwargs: text or kwargs.get("text")
    return tool


def test_text2data_summary_output_streams_llm_summary():
    """摘要输出模式应把 LLM 流式摘要逐段返回。"""
    calls = {}

    class FakeLLM:
        def invoke(self, **kwargs):
            calls.update(kwargs)
            return [_chunk("收入"), _chunk("增长")]

    tool = _create_tool(FakeLLM())

    outputs = list(
        tool._handle_summary_output(
            [{"month": "2026-06", "revenue": "100"}],
            ["month", "revenue"],
            "总结收入",
            {"provider": "fake"},
        )
    )

    assert outputs == ["收入", "增长"]
    assert calls["model_config"] == {"provider": "fake"}
    assert calls["stream"] is True
    assert "总结收入" in calls["prompt_messages"][0].content


def test_text2data_summary_output_falls_back_to_json_when_llm_fails():
    """摘要生成失败时应回退返回 JSON 数据，避免工具无结果。"""
    class FailingLLM:
        def invoke(self, **kwargs):
            raise RuntimeError("llm down")

    tool = _create_tool(FailingLLM())

    outputs = list(
        tool._handle_summary_output(
            [{"month": "2026-06", "revenue": "100"}],
            ["month", "revenue"],
            "总结收入",
            {"provider": "fake"},
        )
    )

    assert len(outputs) == 1
    assert json.loads(outputs[0]) == [{"month": "2026-06", "revenue": "100"}]
