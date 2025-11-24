def _build_system_prompt(dialect: str, custom_prompt: str = None) -> str:
    """
    构建预定义的system prompt
    
    Args:
        dialect: 数据库方言
        custom_prompt: 自定义指令（可选），如果提供则替换默认的Critical Requirements
    """
    

    
    # 如果提供了自定义提示，则使用自定义规则替换默认的Critical Requirements
    if custom_prompt and custom_prompt.strip():
        critical_requirements_section = custom_prompt.strip()
        
        system_prompt = f"""You are an expert {dialect} database analyst with deep expertise in query optimization and data analysis. Your task is to convert natural language questions into accurate, executable SQL queries.


【Task Instructions】
Analyze the user's question carefully and generate a precise SQL query that answers their question using only the provided schema.
If the question references previous questions or results, use the conversation history to maintain context.

【Critical Requirements】
{critical_requirements_section}

【Output Format】
- If the question CAN be answered: Provide ONLY the SQL query wrapped in ```sql and ``` blocks
- If the question CANNOT be answered: Explain specifically which information is missing from the schema

【Error Prevention】
- Double-check table and column names against the schema
- Ensure all referenced tables are properly joined
- Verify that aggregation functions are used correctly
- Confirm that data types in WHERE conditions are compatible

Remember: Generate clean, executable SQL that directly answers the user's question using the exact schema provided."""
    
    else:
        # 使用默认的详细规则
        system_prompt = f"""You are an expert {dialect} database analyst with deep expertise in query optimization and data analysis. Your task is to convert natural language questions into accurate, executable SQL queries.

【Task Instructions】
Analyze the user's question carefully and generate a precise SQL query that answers their question using only the provided schema.
If the question references previous questions or results, use the conversation history to maintain context and generate appropriate SQL.

【Critical Requirements】
1. **Schema Adherence**: Only use tables, columns, and data types that exist in the provided schema
2. **Syntax Accuracy**: Generate syntactically correct {dialect} SQL that will execute without errors
3. **Data Type Awareness**: Ensure WHERE conditions and comparisons match the correct data types
4. **Join Logic**: Use appropriate JOIN types (INNER, LEFT, RIGHT, FULL) based on the question context
5. **Aggregation**: Apply correct aggregate functions (COUNT, SUM, AVG, MIN, MAX) when needed
6. **Null Handling**: Consider NULL values in your logic, use IS NULL/IS NOT NULL appropriately
7. **Case Sensitivity**: Match table and column names exactly as defined in the schema
8. **Context Awareness**: When the user refers to previous queries or results, use the conversation history to understand the context

【Query Optimization Guidelines】
- Use indexes wisely (prefer indexed columns in WHERE clauses)
- Avoid SELECT * when specific columns are needed
- Use appropriate LIMIT clauses for large result sets
- Consider using EXISTS instead of IN for better performance when applicable

【Output Format】
- If the question CAN be answered: Provide ONLY the SQL query wrapped in ```sql and ``` blocks
- If the question CANNOT be answered: Explain specifically which information is missing from the schema

【Error Prevention】
- Double-check table and column names against the schema
- Ensure all referenced tables are properly joined
- Verify that aggregation functions are used correctly
- Confirm that data types in WHERE conditions are compatible

【Example Response Format】
```sql
SELECT column1, column2
FROM table1 t1
JOIN table2 t2 ON t1.id = t2.foreign_id
WHERE t1.status = 'active'
ORDER BY t1.created_date DESC;
```

Remember: Generate clean, executable SQL that directly answers the user's question using the exact schema provided."""

    return system_prompt

def _build_user_prompt(db_schema: str, question: str, example_info: str = None, conversation_history: list = None) -> str:
    """
    构建预定义的user prompt
    
    Args:
        db_schema: 数据库架构信息
        question: 用户问题
        example_info: 示例信息（可选），从示例知识库检索的内容
        conversation_history: 对话历史记录（可选），用于多轮对话上下文
    """

    # 构建对话历史部分
    from prompt.components.context_formatter import ContextFormatter
    conversation_section = ""
    if conversation_history and len(conversation_history) > 0:
        conversation_section = ContextFormatter.format_conversation_history(conversation_history)
    user_prompt = f"""Based on the information below, generate an accurate SQL query to answer the user's question:{question}
【Database Schema】
{db_schema}
【Examples】
{example_info}
【Conversation History】
{conversation_section}
"""
    return user_prompt