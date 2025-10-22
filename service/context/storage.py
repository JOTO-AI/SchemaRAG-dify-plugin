"""
上下文存储实现

提供不同的存储后端实现，支持扩展
"""

import abc
import threading
from typing import Dict, Optional
from datetime import datetime, timedelta
from .models import UserContext


class ContextStorage(abc.ABC):
    """上下文存储抽象基类，支持不同的存储后端"""
    
    @abc.abstractmethod
    def get_context(self, context_key: str) -> Optional[UserContext]:
        """获取指定上下文"""
        pass
    
    @abc.abstractmethod
    def save_context(self, user_context: UserContext) -> bool:
        """保存用户上下文"""
        pass
    
    @abc.abstractmethod
    def delete_context(self, context_key: str) -> bool:
        """删除指定上下文"""
        pass
    
    @abc.abstractmethod
    def cleanup_expired(self, max_age_seconds: int) -> int:
        """清理过期的上下文"""
        pass


class MemoryContextStorage(ContextStorage):
    """内存中的上下文存储实现"""
    
    def __init__(self):
        # 上下文存储字典
        self._contexts: Dict[str, UserContext] = {}
        # 线程锁，保证线程安全
        self._lock = threading.RLock()
        # 上次清理时间
        self._last_cleanup = datetime.now()
    
    def get_context(self, context_key: str) -> Optional[UserContext]:
        """获取用户上下文"""
        with self._lock:
            context = self._contexts.get(context_key)
            if context:
                # 更新访问时间
                context.last_access = datetime.now()
            return context
    
    def save_context(self, user_context: UserContext) -> bool:
        """保存用户上下文"""
        with self._lock:
            self._contexts[user_context.context_key] = user_context
            return True
    
    def delete_context(self, context_key: str) -> bool:
        """删除上下文"""
        with self._lock:
            if context_key in self._contexts:
                del self._contexts[context_key]
                return True
            return False
    
    def cleanup_expired(self, max_age_seconds: int) -> int:
        """清理过期的上下文"""
        cutoff_time = datetime.now() - timedelta(seconds=max_age_seconds)
        expired_count = 0
        
        with self._lock:
            expired_keys = [
                key for key, context in self._contexts.items()
                if context.last_access < cutoff_time
            ]
            
            for key in expired_keys:
                del self._contexts[key]
                expired_count += 1
                
        return expired_count
    
    def get_stats(self) -> Dict[str, int]:
        """获取存储统计信息"""
        with self._lock:
            total_conversations = sum(
                len(ctx.conversations) for ctx in self._contexts.values()
            )
            return {
                "total_contexts": len(self._contexts),
                "total_conversations": total_conversations
            }
