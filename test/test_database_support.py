#!/usr/bin/env python3
"""
测试数据库支持配置
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DatabaseConfig


def test_database_connections():
    """测试不同数据库类型的连接字符串生成"""

    test_configs = [
        {
            "type": "mysql",
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "password",
            "database": "test_db",
        },
        {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "user": "postgres",
            "password": "password",
            "database": "test_db",
        },
        {
            "type": "mssql",
            "host": "localhost",
            "port": 1433,
            "user": "sa",
            "password": "password",
            "database": "test_db",
        },
        {
            "type": "oracle",
            "host": "localhost",
            "port": 1521,
            "user": "system",
            "password": "password",
            "database": "ORCL",
        },
        {
            "type": "dameng",
            "host": "localhost",
            "port": 5236,
            "user": "SYSDBA",
            "password": "SYSDBA",
            "database": "test_db",
        },
    ]

    print("测试数据库连接字符串生成:")
    print("=" * 60)

    for config in test_configs:
        try:
            db_config = DatabaseConfig(
                type=config["type"],
                host=config["host"],
                port=config["port"],
                user=config["user"],
                password=config["password"],
                database=config["database"],
            )

            connection_string = db_config.get_connection_string()
            print(f"✅ {config['type'].upper():>12}: {connection_string}")

        except Exception as e:
            print(f"❌ {config['type'].upper():>12}: 错误 - {e}")

    print("=" * 60)


if __name__ == "__main__":
    test_database_connections()
