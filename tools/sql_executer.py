import pymysql
import psycopg2
from collections.abc import Generator
from typing import Any, Dict, List
import json
import pandas as pd
import re

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

class SQLExecuterTool(Tool):
    """
    SQL Executer Tool
    """

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        """
        Execute SQL queries and return results in specified format.
        """
        # 获取参数
        sql_query = tool_parameters.get("sql")
        output_format = tool_parameters.get("output_format", "json")

        # Detect and clean markdown format from SQL query using regex for better fault tolerance
        match = re.search(r"```(?:sql)?\s*(.*?)\s*```", sql_query, re.DOTALL)
        if match:
            cleaned_sql = match.group(1).strip()
        else:
            # If no markdown block is found, assume the whole input is the query.
            cleaned_sql = sql_query.strip()
        
        sql_query = cleaned_sql

        if not sql_query:
            yield self.create_text_message("Error: SQL query is required.")
            return

        # Security check: only allow SELECT statements
        if not sql_query.lower().strip().startswith('select'):
            yield self.create_text_message("Error: Only SELECT queries are allowed for security reasons.")
            return

        try:
            # 从 provider 获取数据库配置
            credentials = self.runtime.credentials
            db_type = credentials.get("db_type")
            db_host = credentials.get("db_host")
            db_port = int(credentials.get("db_port"))
            db_user = credentials.get("db_user")
            db_password = credentials.get("db_password")
            db_name = credentials.get("db_name")

            if not all([db_type, db_host, db_port, db_user, db_password, db_name]):
                yield self.create_text_message("Error: Database configuration is incomplete in the provider.")
                return

            # 执行查询
            results, columns = self._execute_query(db_type, db_host, db_port, db_user, db_password, db_name, sql_query)

            # 格式化输出
            formatted_output = self._format_output(results, columns, output_format)
            yield self.create_text_message(text=formatted_output)

        except Exception as e:
            yield self.create_text_message(f"An error occurred during SQL execution: {str(e)}")

    def _execute_query(self, db_type, host, port, user, password, dbname, query):
        """
        Connect to the database and execute the query.
        """
        conn = None
        try:
            if db_type == 'mysql':
                conn = pymysql.connect(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    database=dbname,
                    cursorclass=pymysql.cursors.DictCursor
                )
            elif db_type == 'postgresql':
                conn = psycopg2.connect(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    dbname=dbname
                )
            else:
                raise ValueError(f"Unsupported database type: {db_type}")

            with conn.cursor() as cursor:
                cursor.execute(query)
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    results = cursor.fetchall()
                    # For psycopg2, results are tuples, convert to dict
                    if db_type == 'postgresql':
                        results = [dict(zip(columns, row)) for row in results]
                    return results, columns
                else:
                    # For queries that don't return rows (e.g., INSERT, UPDATE)
                    return [{"status": "success", "rows_affected": cursor.rowcount}], ["result"]

        finally:
            if conn:
                conn.close()

    def _format_output(self, results: List[Dict], columns: List[str], format_type: str) -> str:
        """
        Format the query results into the specified format.
        """
        if not results:
            return "Query executed successfully, but returned no results."

        df = pd.DataFrame(results, columns=columns)

        if format_type == 'json':
            return df.to_json(orient='records', indent=4, force_ascii=False)
        elif format_type == 'md':
            return df.to_markdown(index=False)
        else:
            return "Unsupported output format. Please use 'json' or 'md'."
