import sys
import os
from collections.abc import Generator
from typing import Any, Dict, List
import re

import pandas as pd

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)  # 添加上级目录到路径中

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from service.database_service import DatabaseService


class SQLExecuterTool(Tool):
    """
    SQL Executer Tool
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_service = DatabaseService()
        # 从 provider 获取数据库配置
        credentials = self.runtime.credentials
        self.db_type = credentials.get("db_type")
        self.db_host = credentials.get("db_host")
        self.db_port = int(credentials.get("db_port"))
        self.db_user = credentials.get("db_user")
        self.db_password = credentials.get("db_password")
        self.db_name = credentials.get("db_name")

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        """
        Execute SQL queries and return results in specified format.
        """
        # 获取参数
        sql_query = tool_parameters.get("sql")
        output_format = tool_parameters.get("output_format", "json")

        try:

            if not all(
                [
                    self.db_type,
                    self.db_host,
                    self.db_port,
                    self.db_user,
                    self.db_password,
                    self.db_name,
                ]
            ):
                yield self.create_text_message(
                    "Error: Database configuration is incomplete in the provider."
                )
                return

            # 执行查询
            results, columns = self.db_service.execute_query(
                self.db_type,
                self.db_host,
                self.db_port,
                self.db_user,
                self.db_password,
                self.db_name,
                sql_query,
            )

            # 格式化输出
            formatted_output = self.db_service._format_output(results, columns, output_format)
            yield self.create_text_message(text=formatted_output)

        except Exception as e:
            yield self.create_text_message(
                f"An error occurred during SQL execution: {str(e)}"
            )


