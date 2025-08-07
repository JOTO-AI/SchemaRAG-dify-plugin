def _data_summary_prompt(data_content: str, query: str, custom_rules: str = None) -> str:
    """
    构建数据摘要prompt，传入数据内容，返回摘要信息
    """
    custom_rules_section = ""
    if custom_rules and custom_rules.strip():
        custom_rules_section = f"""
        【Custom Analysis Rules】
        {custom_rules}
        Please follow these custom rules when analyzing the data.
        """

    system_prompt = f"""You are an expert data analyst with deep expertise in data interpretation, statistical analysis, and business intelligence. Your task is to analyze the provided data and generate comprehensive insights based on the user's query.
【Query】
{query}
【Data Content】
{data_content}
【Custom Rules】
{custom_rules_section}
【Output Requirements】
- Use the same language as the user's query
- Provide a structured analysis with clear sections
- Include specific numbers and percentages where relevant
- Highlight significant trends, patterns, or outliers
- Offer actionable recommendations based on the findings
- Be concise but comprehensive in your analysis

Please provide a thorough yet concise analysis that addresses the user's specific query while offering valuable insights into the data."""

    return system_prompt

