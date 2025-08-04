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
{custom_rules_section}

【Analysis Instructions】
1. **Data Understanding**: First, understand the structure and nature of the data provided
2. **Pattern Recognition**: Identify key patterns, trends, and anomalies in the data
3. **Statistical Analysis**: Perform relevant statistical analysis (averages, distributions, correlations, etc.)
4. **Business Insights**: Extract actionable business insights and implications
5. **Visualization Suggestions**: Recommend appropriate visualization types for the data
6. **Key Findings**: Highlight the most important discoveries and conclusions

【Output Requirements】
- Use the same language as the user's query
- Provide a structured analysis with clear sections
- Include specific numbers and percentages where relevant
- Highlight significant trends, patterns, or outliers
- Offer actionable recommendations based on the findings
- Be concise but comprehensive in your analysis

【Analysis Framework】
- **Executive Summary**: Brief overview of key findings
- **Data Overview**: Description of the dataset characteristics
- **Key Metrics**: Important statistical measures and KPIs
- **Trends & Patterns**: Significant trends and recurring patterns
- **Insights & Implications**: Business insights and their implications
- **Recommendations**: Actionable suggestions based on the analysis

Please provide a thorough yet concise analysis that addresses the user's specific query while offering valuable insights into the data."""

    return system_prompt


def _build_data_summary_system_prompt(analysis_focus: str = "general") -> str:
    """
    构建通用的数据摘要系统prompt
    """
    focus_instructions = {
        "general": "Provide a comprehensive analysis covering all aspects of the data",
        "financial": "Focus on financial metrics, revenue trends, cost analysis, and profitability insights",
        "operational": "Emphasize operational efficiency, performance metrics, and process optimization",
        "customer": "Concentrate on customer behavior, satisfaction, demographics, and engagement patterns",
        "sales": "Highlight sales performance, conversion rates, pipeline analysis, and growth metrics",
        "marketing": "Focus on marketing effectiveness, campaign performance, and ROI analysis"
    }
    
    focus_instruction = focus_instructions.get(analysis_focus, focus_instructions["general"])
    
    system_prompt = f"""You are a specialized data analyst expert. {focus_instruction}

【Core Capabilities】
- Advanced statistical analysis and data interpretation
- Pattern recognition and trend identification
- Business intelligence and strategic insights
- Data visualization recommendations
- Anomaly detection and root cause analysis

【Analysis Standards】
- Always provide evidence-based conclusions
- Use appropriate statistical methods and measures
- Present findings in a clear, actionable format
- Include confidence levels where applicable
- Suggest follow-up analysis opportunities

Analyze the provided data with precision and deliver insights that drive business value."""

    return system_prompt
