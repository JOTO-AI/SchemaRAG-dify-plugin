"""
上下文管理器

负责高级别的上下文操作和管理
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import uuid

from .models import UserContext, Conversation
from .storage import ContextStorage, MemoryContextStorage


class ContextManager:
    """上下文管理器，负责高级别的上下文操作"""
    
    # 默认配置
    DEFAULT_MEMORY_WINDOW = 3         # 默认记忆窗口大小
    DEFAULT_EXPIRY_TIME = 24 * 3600   # 默认过期时间（24小时）
    CLEANUP_INTERVAL = 3600           # 清理间隔（1小时）
    
    # 类级别的单例存储实例，所有ContextManager实例共享同一个存储
    _shared_storage: Optional[ContextStorage] = None
    
    def __init__(self, storage: Optional[ContextStorage] = None):
        """
        初始化上下文管理器
        
        Args:
            storage: 上下文存储实现，默认使用共享的内存存储
        """
        # 如果没有提供storage且没有共享存储，创建一个
        if storage is None:
            if ContextManager._shared_storage is None:
                ContextManager._shared_storage = MemoryContextStorage()
            self.storage = ContextManager._shared_storage
        else:
            self.storage = storage
            
        self.logger = logging.getLogger(__name__)
        self._last_cleanup = datetime.now()
    
    def _auto_cleanup(self) -> None:
        """自动定期清理过期上下文"""
        now = datetime.now()
        if now - self._last_cleanup > timedelta(seconds=self.CLEANUP_INTERVAL):
            self._last_cleanup = now
            try:
                cleaned = self.storage.cleanup_expired(self.DEFAULT_EXPIRY_TIME)
                if cleaned > 0:
                    self.logger.info(f"自动清理了 {cleaned} 个过期上下文")
            except Exception as e:
                self.logger.error(f"自动清理上下文出错: {e}")
    
    def _get_user_id(self, user_id: Optional[str] = None) -> str:
        """获取或生成用户ID"""
        if user_id:
            return user_id
        # 生成匿名用户ID
        return f"anon_{uuid.uuid4().hex[:8]}"
    
    def get_context(self, user_id: Optional[str] = None, tool_name: str = "text2sql") -> UserContext:
        """
        获取用户上下文，如不存在则创建
        
        Args:
            user_id: 用户ID，如为None则创建匿名ID
            tool_name: 工具名称
            
        Returns:
            用户上下文实例
        """
        # 运行自动清理
        self._auto_cleanup()
        
        # 确保有用户ID
        user_id = self._get_user_id(user_id)
        
        # 构造上下文键
        context_key = f"{user_id}:{tool_name}"
        
        # 尝试获取上下文
        user_context = self.storage.get_context(context_key)
        
        # 不存在则创建新上下文
        if not user_context:
            user_context = UserContext(user_id=user_id, tool_name=tool_name)
            self.storage.save_context(user_context)
            
        return user_context
    
    def add_conversation(
        self, 
        query: str, 
        sql: str,
        user_id: Optional[str] = None,
        tool_name: str = "text2sql",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        添加对话记录
        
        Args:
            query: 用户问题
            sql: 生成的SQL
            user_id: 用户ID，可选
            tool_name: 工具名称，默认为text2sql
            metadata: 额外元数据
        """
        try:
            # 获取用户上下文
            user_context = self.get_context(user_id, tool_name)
            
            # 创建对话记录
            conversation = Conversation(
                query=query,
                sql=sql,
                metadata=metadata or {}
            )
            
            # 添加到上下文
            user_context.add_conversation(conversation)
            
            # 保存上下文
            self.storage.save_context(user_context)
            
            self.logger.debug(f"成功添加对话记录，用户: {user_id}")
        except Exception as e:
            self.logger.error(f"添加对话记录失败: {e}")
    
    def get_conversation_history(
        self,
        user_id: Optional[str] = None,
        tool_name: str = "text2sql",
        window_size: int = DEFAULT_MEMORY_WINDOW
    ) -> List[Dict[str, Any]]:
        """
        获取对话历史
        
        Args:
            user_id: 用户ID，可选
            tool_name: 工具名称
            window_size: 记忆窗口大小
            
        Returns:
            最近window_size轮对话的字典表示
        """
        try:
            # 获取用户上下文
            user_context = self.get_context(user_id, tool_name)
            
            # 获取最近对话
            recent_conversations = user_context.get_recent_conversations(window_size)
            
            # 转换为字典列表
            return [conv.to_dict() for conv in recent_conversations]
        except Exception as e:
            self.logger.error(f"获取对话历史失败: {e}")
            return []
    
    def reset_memory(
        self,
        user_id: Optional[str] = None,
        tool_name: str = "text2sql"
    ) -> bool:
        """
        重置对话记忆
        
        Args:
            user_id: 用户ID，可选
            tool_name: 工具名称
            
        Returns:
            是否成功重置
        """
        try:
            # 确保有用户ID
            user_id = self._get_user_id(user_id)
            
            # 获取用户上下文
            user_context = self.get_context(user_id, tool_name)
            
            # 清空对话历史
            user_context.clear_conversations()
            
            # 保存更新后的上下文
            success = self.storage.save_context(user_context)
            
            if success:
                self.logger.info(f"成功重置用户记忆，用户: {user_id}")
            
            return success
        except Exception as e:
            self.logger.error(f"重置记忆失败: {e}")
            return False
    
    def get_storage_stats(self) -> Dict[str, int]:
        """
        获取存储统计信息
        
        Returns:
            包含统计信息的字典
        """
        if hasattr(self.storage, 'get_stats'):
            return self.storage.get_stats()
        return {}
