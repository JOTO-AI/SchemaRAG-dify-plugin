import re
from typing import Dict, List
import pandas as pd
import pymysql
import psycopg2


class DatabaseService:
    def execute_query(self, db_type, host, port, user, password, dbname, query):
        """
        Connect to the database and execute the query.
        """
        conn = None
        try:
            if db_type == "mysql":
                conn = pymysql.connect(
                    host=host,
                    port=port,
                    user=user,
                    password=password,
                    database=dbname,
                    cursorclass=pymysql.cursors.DictCursor,
                )
            elif db_type == "postgresql":
                conn = psycopg2.connect(
                    host=host, port=port, user=user, password=password, dbname=dbname
                )
            else:
                raise ValueError(f"Unsupported database type: {db_type}")
                # Detect and clean markdown format from SQL query using regex for better fault tolerance

            match = re.search(r"```(?:sql)?\s*(.*?)\s*```", query, re.DOTALL)
            if match:
                cleaned_sql = match.group(1).strip()
            else:
                # If no markdown block is found, assume the whole input is the query.
                cleaned_sql = query.strip()

            query = cleaned_sql

            if not query:
                raise ValueError("SQL query cannot be empty.")

            # Security check: only allow SELECT statements
            if not query.lower().strip().startswith("select"):
                raise ValueError(
                    "Only SELECT queries are allowed for security reasons."
                )

            with conn.cursor() as cursor:
                cursor.execute(query)
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    results = cursor.fetchall()
                    # For psycopg2, results are tuples, convert to dict
                    if db_type == "postgresql":
                        results = [dict(zip(columns, row)) for row in results]
                    return results, columns
                else:
                    # For queries that don't return rows (e.g., INSERT, UPDATE)
                    return [{"status": "success", "rows_affected": cursor.rowcount}], [
                        "result"
                    ]

        finally:
            if conn:
                conn.close()

    def _format_output(
        self, results: List[Dict], columns: List[str], format_type: str
    ) -> str:
        """
        Format the query results into the specified format.
        """
        if not results:
            return "Query executed successfully, but returned no results."

        df = pd.DataFrame(results, columns=columns)

        if format_type == "json":
            return df.to_json(orient="records", indent=4, force_ascii=False)
        elif format_type == "md":
            return df.to_markdown(index=False)
        else:
            return "Unsupported output format. Please use 'json' or 'md'."
