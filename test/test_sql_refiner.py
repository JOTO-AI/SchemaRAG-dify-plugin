"""
SQL Refiner 测试用例

测试SQL自动纠错功能的各种场景
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from service.sql_refiner import SQLRefiner
from sqlalchemy.exc import SQLAlchemyError


class TestSQLRefiner(unittest.TestCase):
    """SQL Refiner 测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 创建Mock对象
        self.mock_db_service = Mock()
        self.mock_llm_session = Mock()
        self.mock_logger = Mock()
        
        # 创建Refiner实例
        self.refiner = SQLRefiner(
            db_service=self.mock_db_service,
            llm_session=self.mock_llm_session,
            logger=self.mock_logger
        )
        
        # 测试用的Schema信息
        self.test_schema = """
        TABLE: users
        - id (INT, PRIMARY KEY)
        - username (VARCHAR)
        - email (VARCHAR)
        - created_at (DATETIME)
        
        TABLE: orders
        - id (INT, PRIMARY KEY)
        - user_id (INT, FOREIGN KEY)
        - total_amount (DECIMAL)
        - status (VARCHAR)
        """
        
        self.test_question = "查询所有用户的订单数量"
        self.test_dialect = "mysql"
        self.test_db_config = {
            'db_type': 'mysql',
            'host': 'localhost',
            'port': 3306,
            'user': 'test',
            'password': 'test',
            'dbname': 'testdb'
        }
    
    def test_clean_sql_with_markdown(self):
        """测试清理包含markdown格式的SQL"""
        sql_with_markdown = """
        ```sql
        SELECT * FROM users WHERE id = 1;
        ```
        """
        
        cleaned = self.refiner._clean_sql(sql_with_markdown)
        self.assertEqual(cleaned, "SELECT * FROM users WHERE id = 1;")
    
    def test_clean_sql_without_markdown(self):
        """测试清理不含markdown的SQL"""
        sql = "SELECT * FROM users WHERE id = 1;"
        cleaned = self.refiner._clean_sql(sql)
        self.assertEqual(cleaned, "SELECT * FROM users WHERE id = 1;")
    
    def test_add_limit_for_validation_select(self):
        """测试为SELECT查询添加LIMIT"""
        sql = "SELECT * FROM users"
        result = self.refiner._add_limit_for_validation(sql)
        self.assertTrue("LIMIT 0" in result)
    
    def test_add_limit_for_validation_with_existing_limit(self):
        """测试已有LIMIT的查询不再添加"""
        sql = "SELECT * FROM users LIMIT 10"
        result = self.refiner._add_limit_for_validation(sql)
        self.assertEqual(result, sql)
    
    def test_add_limit_for_validation_non_select(self):
        """测试非SELECT查询不添加LIMIT"""
        sql = "UPDATE users SET status = 'active'"
        result = self.refiner._add_limit_for_validation(sql)
        self.assertEqual(result, sql)
    
    def test_validate_sql_success(self):
        """测试SQL验证成功的情况"""
        # Mock成功的查询执行
        self.mock_db_service.execute_query.return_value = ([], [])
        
        test_sql = "SELECT * FROM users"
        is_valid, error_msg = self.refiner._validate_sql(test_sql, self.test_db_config)
        
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")
    
    def test_validate_sql_failure(self):
        """测试SQL验证失败的情况"""
        # Mock失败的查询执行
        error_message = "Column 'invalid_column' doesn't exist"
        self.mock_db_service.execute_query.side_effect = SQLAlchemyError(error_message)
        
        test_sql = "SELECT invalid_column FROM users"
        is_valid, error_msg = self.refiner._validate_sql(test_sql, self.test_db_config)
        
        self.assertFalse(is_valid)
        self.assertIn("invalid_column", error_msg)
    
    def test_refine_sql_success_first_attempt(self):
        """测试第一次尝试就成功修复SQL"""
        # Mock第一次验证失败，第二次成功
        validation_results = [
            (False, "Column 'name' doesn't exist"),  # 第一次失败
            (True, "")  # 第二次成功
        ]
        self.refiner._validate_sql = Mock(side_effect=validation_results)
        
        # Mock LLM返回修复后的SQL
        mock_response = Mock()
        mock_response.message.content = "SELECT username FROM users"
        self.mock_llm_session.model.llm.invoke.return_value = mock_response
        
        failed_sql = "SELECT name FROM users"
        mock_llm_model = Mock()
        
        refined_sql, success, error_history = self.refiner.refine_sql(
            original_sql=failed_sql,
            schema_info=self.test_schema,
            question=self.test_question,
            dialect=self.test_dialect,
            db_config=self.test_db_config,
            llm_model=mock_llm_model,
            max_iterations=3
        )
        
        self.assertTrue(success)
        self.assertEqual(len(error_history), 1)
        self.assertIn("username", refined_sql)
    
    def test_refine_sql_max_iterations_reached(self):
        """测试达到最大迭代次数仍失败"""
        # Mock所有验证都失败
        self.refiner._validate_sql = Mock(return_value=(False, "Syntax error"))
        
        # Mock LLM每次都返回错误的SQL
        mock_response = Mock()
        mock_response.message.content = "SELECT * FROM invalid_table"
        self.mock_llm_session.model.llm.invoke.return_value = mock_response
        
        failed_sql = "SELECT * FROM nonexistent"
        mock_llm_model = Mock()
        
        refined_sql, success, error_history = self.refiner.refine_sql(
            original_sql=failed_sql,
            schema_info=self.test_schema,
            question=self.test_question,
            dialect=self.test_dialect,
            db_config=self.test_db_config,
            llm_model=mock_llm_model,
            max_iterations=3
        )
        
        self.assertFalse(success)
        self.assertEqual(len(error_history), 3)
    
    def test_refine_sql_llm_returns_empty(self):
        """测试LLM返回空SQL的情况"""
        # Mock第一次验证失败
        self.refiner._validate_sql = Mock(return_value=(False, "Column error"))
        
        # Mock LLM返回空内容
        mock_response = Mock()
        mock_response.message.content = ""
        self.mock_llm_session.model.llm.invoke.return_value = mock_response
        
        failed_sql = "SELECT invalid FROM users"
        mock_llm_model = Mock()
        
        refined_sql, success, error_history = self.refiner.refine_sql(
            original_sql=failed_sql,
            schema_info=self.test_schema,
            question=self.test_question,
            dialect=self.test_dialect,
            db_config=self.test_db_config,
            llm_model=mock_llm_model,
            max_iterations=3
        )
        
        self.assertFalse(success)
        self.assertEqual(len(error_history), 1)
    
    def test_format_refiner_result_success(self):
        """测试成功格式化Refiner结果"""
        original_sql = "SELECT name FROM users"
        refined_sql = "SELECT username FROM users"
        error_history = [
            {"iteration": 1, "sql": original_sql, "error": "Column 'name' doesn't exist"}
        ]
        
        report = self.refiner.format_refiner_result(
            original_sql=original_sql,
            refined_sql=refined_sql,
            success=True,
            error_history=error_history,
            iterations=1
        )
        
        self.assertIn("成功", report)
        self.assertIn("1 次迭代", report)
        self.assertIn(refined_sql, report)
    
    def test_format_refiner_result_failure(self):
        """测试失败格式化Refiner结果"""
        original_sql = "SELECT invalid FROM users"
        refined_sql = "SELECT still_invalid FROM users"
        error_history = [
            {"iteration": 1, "sql": original_sql, "error": "Column 'invalid' doesn't exist"},
            {"iteration": 2, "sql": refined_sql, "error": "Column 'still_invalid' doesn't exist"}
        ]
        
        report = self.refiner.format_refiner_result(
            original_sql=original_sql,
            refined_sql=refined_sql,
            success=False,
            error_history=error_history,
            iterations=2
        )
        
        self.assertIn("失败", report)
        self.assertIn("2 次尝试", report)
        self.assertIn("错误历史", report)


class TestSQLRefinerIntegration(unittest.TestCase):
    """SQL Refiner 集成测试"""
    
    @patch('service.sql_refiner.SQLRefiner._validate_sql')
    @patch('service.sql_refiner.SQLRefiner._generate_refined_sql')
    def test_column_name_correction(self, mock_generate, mock_validate):
        """测试列名纠错场景"""
        # 模拟场景：用户使用了错误的列名 'name'，应该是 'username'
        mock_db_service = Mock()
        mock_llm_session = Mock()
        
        refiner = SQLRefiner(mock_db_service, mock_llm_session)
        
        # 第一次验证失败（错误的列名）
        # 第二次验证成功（修复后的列名）
        mock_validate.side_effect = [
            (False, "Unknown column 'name' in 'field list'"),
            (True, "")
        ]
        
        # Mock生成修复后的SQL
        mock_generate.return_value = "SELECT username FROM users"
        
        failed_sql = "SELECT name FROM users"
        schema_info = "TABLE users: id, username, email"
        
        refined_sql, success, _ = refiner.refine_sql(
            original_sql=failed_sql,
            schema_info=schema_info,
            question="获取用户名",
            dialect="mysql",
            db_config={},
            llm_model=Mock(),
            max_iterations=3
        )
        
        self.assertTrue(success)
        self.assertIn("username", refined_sql)


if __name__ == '__main__':
    unittest.main()