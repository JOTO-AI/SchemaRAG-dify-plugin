"""
上下文格式化组件

负责将对话历史格式化为提示词片段
"""

from typing import List, Dict, Any, Optional


class ContextFormatter:
    """上下文格式化组件，负责将上下文历史格式化为合适的提示词片段"""
    
    @staticmethod
    def format_conversation_history(
        conversation_history: List[Dict[str, Any]], 
        max_length: Optional[int] = None
    ) -> str:
        """
        将对话历史格式化为提示词片段
        
        Args:
            conversation_history: 对话历史列表
            max_length: 可选的最大长度限制
            
        Returns:
            格式化后的文本
        """
        if not conversation_history:
            return ""
            
        history_items = []
        for i, conv in enumerate(conversation_history, 1):
            query = conv.get('query', '')
            sql = conv.get('sql', '')
            
            # 如果有最大长度限制，截断过长的内容
            if max_length:
                if len(query) > max_length:
                    query = query[:max_length] + "..."
                if len(sql) > max_length:
                    sql = sql[:max_length] + "..."
            
            history_items.append(f"问题 {i}: {query}\nSQL {i}: {sql}")
        
        history_content = "\n\n".join(history_items)
        
        return history_content
    
    @staticmethod
    def format_for_llm(conversation_history: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        将对话历史格式化为LLM可以理解的消息格式
        
        Args:
            conversation_history: 对话历史列表
            
        Returns:
            格式化后的消息列表
        """
        messages = []
        for conv in conversation_history:
            # 用户问题
            messages.append({
                "role": "user",
                "content": conv.get('query', '')
            })
            # 助手回答（SQL）
            messages.append({
                "role": "assistant", 
                "content": conv.get('sql', '')
            })
        return messages
    
    @staticmethod
    def should_include_context(
        conversation_history: List[Dict[str, Any]], 
        current_query: str
    ) -> bool:
        """
        判断是否应该包含上下文历史
        
        通过简单的启发式规则判断当前查询是否依赖历史上下文
        
        Args:
            conversation_history: 对话历史列表
            current_query: 当前查询
            
        Returns:
            是否应该包含上下文
        """
        if not conversation_history:
            return False
        
        # 检查查询中是否包含引用词
        reference_keywords = [
            '它', '这', '那', '上面', '上述', '刚才', '之前', '前面',
            '这个', '那个', '这些', '那些', '同样', '也', '还',
            'it', 'this', 'that', 'above', 'previous', 'same', 'also'
        ]
        
        query_lower = current_query.lower()
        for keyword in reference_keywords:
            if keyword in query_lower:
                return True
        
        return False
