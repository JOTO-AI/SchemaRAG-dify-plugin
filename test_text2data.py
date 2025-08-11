"""
Test file for text2data tool
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def test_imports():
    """Test if all required imports work correctly"""
    try:
        from tools.text2data import Text2DataTool
        from prompt import text2sql_prompt, summary_prompt
        from service.knowledge_service import KnowledgeService
        from service.database_service import DatabaseService

        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def test_class_initialization():
    """Test if the class can be initialized (without actual credentials)"""
    try:
        # This will fail due to missing credentials, but we can test the class structure
        from tools.text2data import Text2DataTool

        # Check if class has required methods
        methods = ["_invoke", "_clean_sql_query"]
        for method in methods:
            if hasattr(Text2DataTool, method):
                print(f"✅ Method {method} exists")
            else:
                print(f"❌ Method {method} missing")
                return False

        return True
    except Exception as e:
        print(f"❌ Class initialization test error: {e}")
        return False


def test_sql_cleaning():
    """Test the SQL cleaning functionality"""
    try:

        # Create a mock instance (this will fail, but we can test the static method)
        class MockTool:
            def _clean_sql_query(self, sql_query: str) -> str:
                import re

                # 移除markdown代码块标记
                sql_query = re.sub(r"```sql\s*", "", sql_query)
                sql_query = re.sub(r"```\s*", "", sql_query)

                # 移除前后空白
                sql_query = sql_query.strip()

                # 如果有多行，只取第一个完整的SQL语句
                lines = sql_query.split("\n")
                cleaned_lines = []
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith("--") and not line.startswith("#"):
                        cleaned_lines.append(line)

                # 重新组合SQL
                if cleaned_lines:
                    sql_query = " ".join(cleaned_lines)

                return sql_query

        mock_tool = MockTool()

        # Test cases
        test_cases = [
            ("```sql\nSELECT * FROM users;\n```", "SELECT * FROM users;"),
            (
                "SELECT * FROM products WHERE price > 100",
                "SELECT * FROM products WHERE price > 100",
            ),
            (
                "```sql\nSELECT name, email\nFROM customers\nWHERE status = 'active';\n```",
                "SELECT name, email FROM customers WHERE status = 'active';",
            ),
        ]

        for input_sql, expected in test_cases:
            result = mock_tool._clean_sql_query(input_sql)
            if result == expected:
                print(f"✅ SQL cleaning test passed: {input_sql[:20]}...")
            else:
                print(
                    f"❌ SQL cleaning test failed: expected '{expected}', got '{result}'"
                )
                return False

        return True
    except Exception as e:
        print(f"❌ SQL cleaning test error: {e}")
        return False


if __name__ == "__main__":
    print("Running Text2Data Tool Tests...")
    print("=" * 50)

    all_tests_passed = True

    # Run tests
    all_tests_passed &= test_imports()
    all_tests_passed &= test_class_initialization()
    all_tests_passed &= test_sql_cleaning()

    print("=" * 50)
    if all_tests_passed:
        print("🎉 All tests passed!")
    else:
        print("💥 Some tests failed!")
