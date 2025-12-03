"""
SQL Refiner Prompt - 用于SQL自动纠错的提示词模板
"""

def _build_refiner_system_prompt(dialect: str) -> str:
    """
    构建 SQL Refiner 的 system prompt
    
    Args:
        dialect: 数据库方言 (mysql, postgresql, mssql, oracle, dameng)
    
    Returns:
        System prompt 字符串
    """
    system_prompt = f"""You are an expert {dialect} SQL debugger and error correction specialist. Your task is to analyze failed SQL queries, identify the root cause of errors, and generate corrected SQL that will execute successfully.

【Your Capabilities】
1. **Error Analysis**: Deeply understand database error messages and tracebacks
2. **Schema Mapping**: Map hallucinated or incorrect column/table names to actual schema entities
3. **Dialect Expertise**: Correct syntax issues specific to {dialect}
4. **Logic Correction**: Fix logical errors in JOINs, aggregations, and conditions
5. **Type Handling**: Resolve data type mismatches and conversion issues

【Critical Rules】
1. **Schema Adherence**: Only use tables and columns that exist in the provided schema
2. **Error Focus**: Address the specific error mentioned in the error message
3. **Minimal Changes**: Make only necessary changes to fix the error
4. **Syntax Correctness**: Ensure the corrected SQL is syntactically valid for {dialect}
5. **Learning from History**: Avoid repeating errors from previous iterations

【Common Error Patterns】
- "Unknown column 'X' in 'field list'" → Check schema for correct column name or similar alternatives
- "Table 'Y' doesn't exist" → Verify table name spelling and case sensitivity
- "Syntax error near 'Z'" → Review {dialect} syntax rules for that construct
- "Data type mismatch" → Add appropriate type casting (CAST/CONVERT)
- "Ambiguous column name" → Add proper table aliases
- "Invalid use of GROUP BY" → Ensure all non-aggregated columns are in GROUP BY

【Output Format】
Provide ONLY the corrected SQL query wrapped in ```sql and ``` blocks. Do not include explanations unless the query cannot be fixed.

【Example Response】
```sql
SELECT t1.customer_id, t1.customer_name, COUNT(t2.order_id) as order_count
FROM customers t1
LEFT JOIN orders t2 ON t1.id = t2.customer_id
WHERE t1.status = 'active'
GROUP BY t1.customer_id, t1.customer_name
ORDER BY order_count DESC;
```

Remember: Your goal is to generate executable SQL that will run without errors on the {dialect} database."""

    return system_prompt


def _build_refiner_user_prompt(
    schema_info: str,
    question: str,
    failed_sql: str,
    error_message: str,
    dialect: str,
    iteration: int,
    error_history: list = None
) -> str:
    """
    构建 SQL Refiner 的 user prompt
    
    Args:
        schema_info: 数据库 Schema 信息
        question: 原始用户问题
        failed_sql: 失败的 SQL 查询
        error_message: 数据库返回的错误信息
        dialect: 数据库方言
        iteration: 当前迭代次数
        error_history: 历史错误记录列表
    
    Returns:
        User prompt 字符串
    """
    
    # 构建历史错误部分
    history_section = ""
    if error_history and len(error_history) > 0:
        history_section = "\n【Previous Error History】\n"
        for idx, err in enumerate(error_history, 1):
            history_section += f"\nAttempt {idx}:\n"
            history_section += f"SQL: {err.get('sql', 'N/A')}\n"
            history_section += f"Error: {err.get('error', 'N/A')}\n"
        history_section += "\nIMPORTANT: Do not repeat the same mistakes from previous attempts!\n"
    
    user_prompt = f"""A SQL query has failed to execute. Please analyze the error and generate a corrected version.

【Original Question】
{question}

【Database Schema】
{schema_info}

【Failed SQL Query】
```sql
{failed_sql}
```

【Error Message】
```
{error_message}
```

【Database Dialect】
{dialect}

【Current Iteration】
{iteration} / 3
{history_section}

【Task】
1. Analyze the error message carefully to identify the root cause
2. Check the schema to find correct table and column names
3. Generate a corrected SQL query that addresses the error
4. Ensure the corrected SQL uses only entities from the provided schema
5. Make sure the SQL is syntactically correct for {dialect}

Generate ONLY the corrected SQL query without any additional explanation."""

    return user_prompt


def _build_validation_error_message(
    sql: str,
    error: Exception,
    db_type: str
) -> str:
    """
    构建格式化的验证错误消息
    
    Args:
        sql: 执行失败的 SQL
        error: 异常对象
        db_type: 数据库类型
    
    Returns:
        格式化的错误消息
    """
    error_type = type(error).__name__
    error_msg = str(error)
    
    formatted_message = f"""
SQL Execution Failed on {db_type.upper()}

Error Type: {error_type}

Error Details:
{error_msg}

Failed SQL:
{sql}

Please analyze this error and generate a corrected SQL query.
"""
    return formatted_message.strip()