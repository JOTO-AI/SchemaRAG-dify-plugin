"""
工具参数验证模块
提供各种工具的参数验证和提取功能
"""
from typing import Any, Tuple, Union, Optional


def validate_and_extract_text2sql_parameters(
    tool_parameters: dict[str, Any],
    max_content_length: int = 10000,
    default_top_k: int = 5,
    default_dialect: str = "mysql",
    default_retrieval_model: str = "semantic_search",
    default_memory_window: int = 3
) -> Union[Tuple[str, Any, str, str, int, str, str, str, bool, int, bool, bool], str]:
    """
    验证并提取Text2SQL工具参数
    
    参数:
        tool_parameters: 工具参数字典
        max_content_length: 最大内容长度限制
        default_top_k: 默认top_k值
        default_dialect: 默认数据库方言
        default_retrieval_model: 默认检索模型
        default_memory_window: 默认记忆窗口大小
    
    返回:
        成功时返回参数元组: (dataset_id, llm_model, content, dialect, top_k, 
                          retrieval_model, custom_prompt, example_dataset_id, 
                          memory_enabled, memory_window_size, reset_memory, cache_enabled)
        失败时返回错误消息字符串
    """
    # 验证必要参数
    dataset_id = tool_parameters.get("dataset_id")
    if not dataset_id or not dataset_id.strip():
        return "缺少知识库ID"

    llm_model = tool_parameters.get("llm")
    if not llm_model:
        return "缺少LLM模型配置"

    content = tool_parameters.get("content")
    if not content or not content.strip():
        return "缺少问题内容"

    # 检查内容长度
    if len(content) > max_content_length:
        return f"问题内容过长，最大允许 {max_content_length} 字符，当前 {len(content)} 字符"

    # 获取可选参数并设置默认值
    dialect = tool_parameters.get("dialect", default_dialect)
    if dialect not in ["mysql", "postgresql", "sqlite", "oracle", "sqlserver", "mssql", "dameng", "doris"]:
        return f"不支持的数据库方言: {dialect}"

    top_k = tool_parameters.get("top_k", default_top_k)
    try:
        top_k = int(top_k)
        if top_k <= 0 or top_k > 50:
            return "top_k 必须在 1-50 之间"
    except (ValueError, TypeError):
        return "top_k 必须是有效的整数"

    retrieval_model = tool_parameters.get(
        "retrieval_model", default_retrieval_model
    )
    if retrieval_model not in [
        "semantic_search",
        "keyword_search",
        "hybrid_search",
        "full_text_search",
    ]:
        return f"不支持的检索模型: {retrieval_model}"

    # 获取自定义提示词（可选参数）
    custom_prompt = tool_parameters.get("custom_prompt", "")
    if custom_prompt and not isinstance(custom_prompt, str):
        return "自定义提示词必须是字符串类型"

    # 获取示例知识库ID（可选参数）
    example_dataset_id = tool_parameters.get("example_dataset_id", "")
    if example_dataset_id and not isinstance(example_dataset_id, str):
        return "示例知识库ID必须是字符串类型"
    
    # 获取记忆相关参数
    memory_enabled = tool_parameters.get("memory_enabled", "False")
    # 处理字符串类型的布尔值（来自select选项）
    if isinstance(memory_enabled, str):
        memory_enabled = memory_enabled.lower() in ['true', '1', 'yes']
    elif not isinstance(memory_enabled, bool):
        memory_enabled = False
    
    memory_window_size = tool_parameters.get("memory_window_size", default_memory_window)
    try:
        memory_window_size = int(memory_window_size)
        if memory_window_size < 1 or memory_window_size > 10:
            return "memory_window_size 必须在 1-10 之间"
    except (ValueError, TypeError):
        return "memory_window_size 必须是有效的整数"
    
    reset_memory = tool_parameters.get("reset_memory", "False")
    # 处理字符串类型的布尔值（来自select选项）
    if isinstance(reset_memory, str):
        reset_memory = reset_memory.lower() in ['true', '1', 'yes']
    elif not isinstance(reset_memory, bool):
        reset_memory = False
    
    # 获取缓存启用参数
    cache_enabled = tool_parameters.get("cache_enabled", "true")
    # 处理字符串类型的布尔值（来自select选项）
    if isinstance(cache_enabled, str):
        cache_enabled = cache_enabled.lower() in ['true', '1', 'yes']
    elif not isinstance(cache_enabled, bool):
        cache_enabled = True  # 默认启用

    return (
        dataset_id.strip(),
        llm_model,
        content.strip(),
        dialect,
        top_k,
        retrieval_model,
        custom_prompt.strip() if custom_prompt else "",
        example_dataset_id.strip() if example_dataset_id else "",
        memory_enabled,
        memory_window_size,
        reset_memory,
        cache_enabled,
    )


def validate_and_extract_sql_executer_parameters(
    tool_parameters: dict[str, Any],
    default_max_rows: int = 500,
    logger=None
) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[str]]:
    """
    验证并提取SQL执行器工具参数
    
    参数:
        tool_parameters: 工具参数字典
        default_max_rows: 默认最大行数
        logger: 可选的日志记录器
    
    返回:
        元组 (sql_query, output_format, max_rows, error_msg)
        - 成功时: (sql查询字符串, 输出格式, 最大行数, None)
        - 失败时: (None, None, None, 错误消息)
    """
    # 验证SQL查询
    sql_query = tool_parameters.get("sql")
    if not sql_query or not sql_query.strip():
        return None, None, None, "SQL查询不能为空"

    # 验证输出格式
    output_format = tool_parameters.get("output_format", "json")
    if output_format not in ["json", "md"]:
        return None, None, None, "输出格式只支持 'json' 或 'md'"

    # 验证max_line参数
    max_line = tool_parameters.get("max_line", default_max_rows)
    try:
        max_rows = int(max_line)
        if max_rows <= 0:
            max_rows = default_max_rows
            if logger:
                logger.warning(f"max_line参数必须大于0，已使用默认值{default_max_rows}: {max_line}")
    except (ValueError, TypeError):
        max_rows = default_max_rows
        if logger:
            logger.warning(f"max_line参数无效，已使用默认值{default_max_rows}: {max_line}")

    return sql_query.strip(), output_format, max_rows, None