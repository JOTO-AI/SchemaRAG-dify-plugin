"""
SQL Refiner Service - SQL自动纠错服务

实现基于LLM的SQL错误自动修复功能，通过迭代反馈机制纠正SQL语法错误和逻辑错误
"""

import re
import logging
from typing import Tuple, List, Dict, Any, Optional
from sqlalchemy.exc import SQLAlchemyError
from prompt import sql_refiner_prompt
from dify_plugin.entities.model.message import SystemPromptMessage, UserPromptMessage


class SQLRefiner:
    """
    SQL自动纠错器
    
    通过LLM反馈循环自动修复SQL错误，支持：
    - 语法错误修复
    - 列名/表名映射
    - 类型转换修正
    - JOIN逻辑优化
    """
    
    def __init__(
        self, 
        db_service, 
        llm_session, 
        logger: Optional[logging.Logger] = None
    ):
        """
        初始化SQL Refiner
        
        Args:
            db_service: 数据库服务实例
            llm_session: Dify LLM会话对象
            logger: 日志记录器
        """
        self.db_service = db_service
        self.llm_session = llm_session
        self.logger = logger or logging.getLogger(__name__)
        
    def refine_sql(
        self,
        original_sql: str,
        schema_info: str,
        question: str,
        dialect: str,
        db_config: Dict[str, Any],
        llm_model: Any,
        max_iterations: int = 3
    ) -> Tuple[str, bool, List[Dict]]:
        """
        迭代修复SQL错误
        
        Args:
            original_sql: 原始生成的SQL
            schema_info: 数据库Schema信息
            question: 用户原始问题
            dialect: 数据库方言
            db_config: 数据库配置字典
            llm_model: LLM模型配置
            max_iterations: 最大迭代次数
            
        Returns:
            (修复后的SQL, 是否成功, 错误历史列表)
        """
        self.logger.info(f"开始SQL自动修复流程，最大迭代次数: {max_iterations}")
        
        current_sql = original_sql
        error_history = []
        
        for iteration in range(1, max_iterations + 1):
            self.logger.info(f"SQL修复迭代 {iteration}/{max_iterations}")
            
            # 验证SQL是否可以执行
            is_valid, error_message = self._validate_sql(current_sql, db_config)
            
            if is_valid:
                self.logger.info(f"SQL修复成功！迭代次数: {iteration}")
                return current_sql, True, error_history
            
            # 记录错误历史
            error_record = {
                "iteration": iteration,
                "sql": current_sql,
                "error": error_message
            }
            error_history.append(error_record)
            
            self.logger.warning(f"第{iteration}次尝试失败: {error_message[:200]}")
            
            # 如果达到最大迭代次数，返回失败
            if iteration >= max_iterations:
                self.logger.error(f"达到最大迭代次数({max_iterations})，SQL修复失败")
                return current_sql, False, error_history
            
            # 使用LLM生成修复后的SQL
            try:
                refined_sql = self._generate_refined_sql(
                    schema_info=schema_info,
                    question=question,
                    failed_sql=current_sql,
                    error_message=error_message,
                    dialect=dialect,
                    iteration=iteration,
                    error_history=error_history[:-1],  # 不包括当前错误
                    llm_model=llm_model
                )
                
                if not refined_sql or refined_sql.strip() == "":
                    self.logger.error("LLM返回的修复SQL为空")
                    return current_sql, False, error_history
                
                # 清理SQL
                refined_sql = self._clean_sql(refined_sql)
                
                if refined_sql == current_sql:
                    self.logger.warning("LLM返回的SQL与之前相同，可能陷入循环")
                    return current_sql, False, error_history
                
                current_sql = refined_sql
                self.logger.info(f"生成新的修复SQL，长度: {len(current_sql)}")
                
            except Exception as e:
                self.logger.error(f"生成修复SQL时发生异常: {str(e)}")
                return current_sql, False, error_history
        
        return current_sql, False, error_history
    
    def _validate_sql(
        self, 
        sql: str, 
        db_config: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        验证SQL是否可以成功执行（使用LIMIT 0避免返回大量数据）
        
        Args:
            sql: 待验证的SQL
            db_config: 数据库配置
            
        Returns:
            (是否有效, 错误信息)
        """
        try:
            # 为SELECT查询添加LIMIT 0进行快速验证
            validation_sql = self._add_limit_for_validation(sql)
            
            # 执行验证查询
            _, _ = self.db_service.execute_query(
                db_type=db_config['db_type'],
                host=db_config['host'],
                port=db_config['port'],
                user=db_config['user'],
                password=db_config['password'],
                dbname=db_config['dbname'],
                query=validation_sql
            )
            
            return True, ""
            
        except SQLAlchemyError as e:
            error_msg = str(e)
            self.logger.debug(f"SQL验证失败: {error_msg[:300]}")
            return False, error_msg
            
        except Exception as e:
            error_msg = f"SQL验证时发生未知错误: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def _add_limit_for_validation(self, sql: str) -> str:
        """
        为SELECT查询添加LIMIT 0用于验证（避免返回大量数据）
        
        Args:
            sql: 原始SQL
            
        Returns:
            添加LIMIT的SQL
        """
        sql_lower = sql.lower().strip()
        
        # 只对SELECT查询添加LIMIT
        if not sql_lower.startswith('select'):
            return sql
        
        # 如果已经有LIMIT，不再添加
        if 'limit' in sql_lower:
            return sql
        
        # 移除末尾的分号
        sql = sql.rstrip(';').strip()
        
        # 添加LIMIT 0
        return f"{sql} LIMIT 0"
    
    def _generate_refined_sql(
        self,
        schema_info: str,
        question: str,
        failed_sql: str,
        error_message: str,
        dialect: str,
        iteration: int,
        error_history: List[Dict],
        llm_model: Any
    ) -> str:
        """
        使用LLM生成修复后的SQL
        
        Args:
            schema_info: Schema信息
            question: 用户问题
            failed_sql: 失败的SQL
            error_message: 错误消息
            dialect: 数据库方言
            iteration: 当前迭代次数
            error_history: 历史错误记录
            llm_model: LLM模型配置
            
        Returns:
            修复后的SQL
        """
        # 构建Prompt
        system_prompt = sql_refiner_prompt._build_refiner_system_prompt(dialect)
        user_prompt = sql_refiner_prompt._build_refiner_user_prompt(
            schema_info=schema_info,
            question=question,
            failed_sql=failed_sql,
            error_message=error_message,
            dialect=dialect,
            iteration=iteration,
            error_history=error_history
        )
        
        self.logger.debug(f"调用LLM进行SQL修复，迭代: {iteration}")
        
        # 调用LLM
        response = self.llm_session.model.llm.invoke(
            model_config=llm_model,
            prompt_messages=[
                SystemPromptMessage(content=system_prompt),
                UserPromptMessage(content=user_prompt),
            ],
            stream=False,
        )
        
        # 提取SQL
        refined_sql = ""
        if hasattr(response, "message") and response.message:
            refined_sql = response.message.content.strip() if response.message.content else ""
        
        if not refined_sql:
            raise ValueError("LLM返回的修复SQL为空")
        
        return refined_sql
    
    def _clean_sql(self, sql: str) -> str:
        """
        清理SQL查询（移除markdown格式等）
        
        Args:
            sql: 原始SQL
            
        Returns:
            清理后的SQL
        """
        if not sql:
            return ""
        
        # 移除markdown代码块
        markdown_pattern = re.compile(r"```(?:sql)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
        match = markdown_pattern.search(sql)
        
        if match:
            cleaned_sql = match.group(1).strip()
        else:
            cleaned_sql = sql.strip()
        
        # 移除多余空白
        cleaned_sql = re.sub(r"\s+", " ", cleaned_sql).strip()
        
        return cleaned_sql
    
    def format_refiner_result(
        self,
        original_sql: str,
        refined_sql: str,
        success: bool,
        error_history: List[Dict],
        iterations: int
    ) -> str:
        """
        格式化Refiner结果为可读的报告
        
        Args:
            original_sql: 原始SQL
            refined_sql: 修复后的SQL
            success: 是否成功
            error_history: 错误历史
            iterations: 实际迭代次数
            
        Returns:
            格式化的报告字符串
        """
        if success:
            report = f"""
【SQL自动修复成功】

✅ 经过 {iterations} 次迭代，SQL已成功修复

📝 修复后的SQL:
{refined_sql}
"""
        else:
            report = f"""
【SQL自动修复失败】

❌ 经过 {iterations} 次尝试，仍无法修复SQL错误

🔍 错误历史:
"""
            for idx, err in enumerate(error_history, 1):
                report += f"\n第{idx}次尝试:\n错误: {err.get('error', 'N/A')[:200]}\n"
        
        return report.strip()