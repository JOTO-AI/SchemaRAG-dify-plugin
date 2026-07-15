#!/usr/bin/env python3
"""
测试 Dify 知识库检索服务
"""

from unittest.mock import Mock, patch

import pytest

from service.knowledge_service import KnowledgeService


@pytest.fixture(autouse=True)
def clear_schema_cache():
    """每个测试前清空 schema 检索缓存，避免跨用例污染。"""
    KnowledgeService.retrieve_schema_from_dataset.cache_clear()
    yield
    KnowledgeService.retrieve_schema_from_dataset.cache_clear()


def _response(status_code=200, body=None):
    response = Mock()
    response.status_code = status_code
    response.json.return_value = body or {}
    response.text = ""
    return response


def _service():
    return KnowledgeService("http://dify.example/v1/", "dataset-key")


def test_request_ignores_environment_proxies():
    """知识库检索请求不读取环境代理配置，避免内网 Dify API 误走代理。"""
    response = _response()
    client_instance = Mock()
    client_instance.request.return_value = response
    client_context = Mock()
    client_context.__enter__ = Mock(return_value=client_instance)
    client_context.__exit__ = Mock(return_value=None)

    with patch("service.knowledge_service.httpx.Client", return_value=client_context) as client:
        result = _service()._request("GET", "http://dify.example/v1/datasets")

    assert result is response
    client.assert_called_once_with(timeout=30.0, trust_env=False)
    client_instance.request.assert_called_once_with(
        "GET",
        "http://dify.example/v1/datasets",
        headers={
            "Authorization": "Bearer dataset-key",
            "Content-Type": "application/json",
        },
    )


def _dataset_retrieval_response(search_method="semantic_search", **overrides):
    retrieval_model = {
        "search_method": search_method,
        "reranking_enable": False,
        "reranking_model": {
            "reranking_provider_name": "",
            "reranking_model_name": "",
        },
        "top_k": 2,
        "score_threshold_enabled": False,
    }
    retrieval_model.update(overrides)
    return _response(body={"retrieval_model_dict": retrieval_model})


def test_retrieve_schema_from_dataset_posts_expected_payload_and_joins_segments():
    """主检索路径应构造正确 payload，并拼接 records 中的 segment content。"""
    response = _response(
        body={
            "records": [
                {"segment": {"content": "table users"}},
                {"segment": {"content": "table orders"}},
                {"segment": {}},
                {},
            ]
        }
    )

    service = _service()
    with patch.object(
        service,
        "_request",
        side_effect=[_dataset_retrieval_response(), response],
    ) as request:
        content = service.retrieve_schema_from_dataset(
            "dataset-1",
            "用户表",
            top_k=3,
            retrieval_model="hybrid_search",
        )

    assert content == "table users\\n\\ntable orders"
    assert request.call_count == 2
    assert request.call_args_list[0].args == (
        "GET",
        "http://dify.example/v1/datasets/dataset-1",
    )
    url = request.call_args_list[1].args[1]
    payload = request.call_args_list[1].kwargs["json"]
    assert url == "http://dify.example/v1/datasets/dataset-1/retrieve"
    assert payload["query"] == "用户表"
    assert payload["retrieval_model"]["top_k"] == 3
    assert payload["retrieval_model"]["search_method"] == "hybrid_search"


def test_retrieve_schema_from_dataset_keeps_dataset_retrieval_config_by_default():
    """默认检索方式应沿用 Dify 知识库自身配置，只覆盖 top_k。"""
    service = _service()
    dataset_response = _dataset_retrieval_response(
        search_method="full_text_search",
        reranking_enable=True,
        reranking_mode="weighted_score",
        weights={
            "weight_type": "customized",
            "vector_setting": {
                "vector_weight": 0.3,
                "embedding_provider_name": "openai",
                "embedding_model_name": "text-embedding-3-small",
            },
            "keyword_setting": {"keyword_weight": 0.7},
        },
        score_threshold_enabled=True,
        score_threshold=0.2,
    )
    retrieve_response = _response(body={"records": []})

    with patch.object(
        service,
        "_request",
        side_effect=[dataset_response, retrieve_response],
    ) as request:
        service.retrieve_schema_from_dataset(
            "dataset-1",
            "用户表",
            top_k=6,
            retrieval_model="semantic_search",
        )

    payload = request.call_args_list[1].kwargs["json"]
    model = payload["retrieval_model"]
    assert model["search_method"] == "full_text_search"
    assert model["top_k"] == 6
    assert model["reranking_mode"] == "weighted_score"
    assert model["weights"]["keyword_setting"]["keyword_weight"] == 0.7
    assert model["score_threshold"] == 0.2


def test_retrieve_schema_from_dataset_falls_back_when_retrieve_api_fails():
    """主检索 API 非 200 时应进入文档片段 fallback。"""
    service = _service()

    with patch.object(
        service,
        "_request",
        side_effect=[_dataset_retrieval_response(), _response(status_code=500)],
    ), patch.object(
        service,
        "_fallback_retrieve_documents",
        return_value="fallback content",
    ) as fallback:
        content = service.retrieve_schema_from_dataset("dataset-1", "query")

    assert content == "fallback content"
    fallback.assert_called_once_with("dataset-1")


def test_retrieve_schema_from_dataset_uses_cache_for_identical_queries():
    """相同检索参数应命中缓存，避免重复 HTTP 调用。"""
    response = _response(body={"records": [{"segment": {"content": "schema"}}]})

    service = _service()
    with patch.object(
        service,
        "_request",
        side_effect=[_dataset_retrieval_response(), response],
    ) as request:
        first = service.retrieve_schema_from_dataset("dataset-1", "  查询 用户 ")
        second = service.retrieve_schema_from_dataset("dataset-1", "查询 用户")

    assert first == "schema"
    assert second == "schema"
    assert request.call_count == 2


def test_fallback_retrieve_documents_limits_documents_and_collects_segments():
    """文档 fallback 只读取前 3 个文档，并拼接片段内容。"""
    service = _service()
    documents_response = _response(
        body={
            "data": [
                {"id": "doc-1"},
                {"id": "doc-2"},
                {"id": "doc-3"},
                {"id": "doc-4"},
                {"name": "missing id"},
            ]
        }
    )

    with patch.object(
        service,
        "_request",
        return_value=documents_response,
    ) as request, patch.object(
        service,
        "_get_document_segments",
        side_effect=[["a", "b"], [], ["c"]],
    ) as get_segments:
        content = service._fallback_retrieve_documents("dataset-1")

    assert content == "a\\n\\nb\\n\\nc"
    request.assert_called_once_with(
        "GET",
        "http://dify.example/v1/datasets/dataset-1/documents",
    )
    assert get_segments.call_count == 3


def test_get_document_segments_limits_to_first_five_nonempty_segments():
    """文档片段读取只返回前 5 个非空 content。"""
    response = _response(
        body={
            "data": [
                {"content": "s1"},
                {"content": ""},
                {"content": "s2"},
                {"content": "s3"},
                {"content": "s4"},
                {"content": "s5"},
                {"content": "s6"},
            ]
        }
    )

    service = _service()
    with patch.object(service, "_request", return_value=response) as request:
        segments = service._get_document_segments("dataset-1", "doc-1")

    assert segments == ["s1", "s2", "s3", "s4"]
    request.assert_called_once_with(
        "GET",
        "http://dify.example/v1/datasets/dataset-1/documents/doc-1/segments",
    )


def test_retrieve_schema_from_multiple_datasets_delegates_single_dataset():
    """单个知识库 ID 走单库检索路径。"""
    service = _service()

    with patch.object(
        service,
        "retrieve_schema_from_dataset",
        return_value="single schema",
    ) as retrieve:
        content = service.retrieve_schema_from_multiple_datasets(
            " dataset-1 ",
            "query",
            top_k=7,
            retrieval_model="keyword_search",
        )

    assert content == "single schema"
    retrieve.assert_called_once_with("dataset-1", "query", 7, "keyword_search")


def test_retrieve_schema_from_multiple_datasets_merges_async_results():
    """多个知识库结果应带来源标题并过滤空内容。"""
    service = _service()

    async def fake_async(dataset_ids, query, top_k, retrieval_model):
        assert dataset_ids == ["a", "b", "c"]
        assert query == "query"
        assert top_k == 2
        assert retrieval_model == "semantic_search"
        return [("a", "schema-a"), ("b", ""), ("c", "schema-c")]

    with patch.object(service, "_retrieve_from_multiple_datasets_async", new=fake_async):
        content = service.retrieve_schema_from_multiple_datasets(
            "a, b, c",
            "query",
            top_k=2,
        )

    assert content == "=== 知识库 a ===\\nschema-a\\n\\n=== 知识库 c ===\\nschema-c"


def test_retrieve_schema_from_multiple_datasets_falls_back_on_async_failure():
    """多库异步检索异常时应降级到同步检索。"""
    service = _service()

    with patch.object(
        service,
        "_retrieve_from_multiple_datasets_async",
        side_effect=RuntimeError("event loop failed"),
    ), patch.object(
        service,
        "_fallback_retrieve_multiple_datasets",
        return_value="fallback multi",
    ) as fallback:
        content = service.retrieve_schema_from_multiple_datasets("a,b", "query")

    assert content == "fallback multi"
    fallback.assert_called_once_with(["a", "b"], "query", 5, "semantic_search")


def test_dataset_info_and_list_datasets_parse_success_and_failure_responses():
    """数据集信息和列表接口应在成功时解析 JSON，失败时返回空值。"""
    service = _service()

    with patch.object(
        service,
        "_request",
        side_effect=[
            _response(body={"id": "dataset-1"}),
            _response(status_code=404),
            _response(body={"data": [{"id": "dataset-1"}]}),
            _response(status_code=500),
        ],
    ):
        assert service.get_dataset_info("dataset-1") == {"id": "dataset-1"}
        assert service.get_dataset_info("missing") is None
        assert service.list_datasets() == [{"id": "dataset-1"}]
        assert service.list_datasets() == []
