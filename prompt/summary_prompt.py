def _data_summary_prompt(data_content: str, query: str) -> str:
    """
    构建数据摘要prompt，传入数据内容，返回摘要信息
    """
    system_prompt = f"""Your task is to analyze the following data content and provide a concise summary to answer the query.

        【Query】
        {query}
        
        【Data】
        {data_content}

        Please provide a summary of the above data and user language from the query.
        """

    return system_prompt
