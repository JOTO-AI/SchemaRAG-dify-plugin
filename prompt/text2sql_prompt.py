
def _build_system_prompt(dialect: str, db_schema: str, question: str) -> str:
        """
        构建预定义的system prompt
        """
        system_prompt = f"""You are now a {dialect} data analyst, and you are given a database schema as follows:

        【Schema】
        {db_schema}

        Please read and understand the database schema carefully, and generate an executable SQL based on the user's question and evidence. The generated SQL is protected by ```sql and ```.

        Requirements:
        1. Use {dialect} syntax for the SQL query
        2. Only use tables and columns that exist in the provided schema
        3. Make sure the SQL is syntactically correct and executable
        4. If the question cannot be answered with the given schema, explain why
        5. Include appropriate WHERE clauses, JOINs, and aggregations as needed
        6. Always wrap the final SQL query in ```sql and ``` code blocks
        """

        return system_prompt
