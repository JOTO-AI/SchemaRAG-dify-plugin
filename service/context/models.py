"""
上下文数据模型

定义对话和用户上下文的数据结构
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class Conversation:
    """单轮对话数据模型"""
    
    query: str  # 用户问题
    sql: str    # 生成的SQL
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)  # 存储额外信息，如数据库方言、架构等
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，便于存储和序列化"""
        return {
            "query": self.query,
            "sql": self.sql,
            "timestamp": self.timestamp.timestamp(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Conversation":
        """从字典创建对话实例"""
        ts = data.get("timestamp")
        if isinstance(ts, (int, float)):
            timestamp = datetime.fromtimestamp(ts)
        else:
            timestamp = datetime.now()
            
        return cls(
            query=data.get("query", ""),
            sql=data.get("sql", ""),
            timestamp=timestamp,
            metadata=data.get("metadata", {})
        )


@dataclass
class UserContext:
    """用户上下文数据模型"""
    
    user_id: str
    tool_name: str = "text2sql"
    conversations: List[Conversation] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_access: datetime = field(default_factory=datetime.now)
    
    @property
    def context_key(self) -> str:
        """获取上下文键"""
        return f"{self.user_id}:{self.tool_name}"
    
    def add_conversation(self, conversation: Conversation) -> None:
        """添加对话记录"""
        self.conversations.append(conversation)
        self.last_access = datetime.now()
    
    def get_recent_conversations(self, window_size: int) -> List[Conversation]:
        """获取最近的对话记录"""
        return self.conversations[-min(window_size, len(self.conversations)):]
    
    def clear_conversations(self) -> None:
        """清空对话历史"""
        self.conversations = []
        self.last_access = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "user_id": self.user_id,
            "tool_name": self.tool_name,
            "conversations": [conv.to_dict() for conv in self.conversations],
            "created_at": self.created_at.timestamp(),
            "last_access": self.last_access.timestamp()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserContext":
        """从字典创建用户上下文实例"""
        user_context = cls(
            user_id=data.get("user_id", ""),
            tool_name=data.get("tool_name", "text2sql")
        )
        
        # 转换时间戳
        created_ts = data.get("created_at")
        if isinstance(created_ts, (int, float)):
            user_context.created_at = datetime.fromtimestamp(created_ts)
            
        access_ts = data.get("last_access")
        if isinstance(access_ts, (int, float)):
            user_context.last_access = datetime.fromtimestamp(access_ts)
            
        # 加载对话历史
        for conv_data in data.get("conversations", []):
            user_context.conversations.append(Conversation.from_dict(conv_data))
            
        return user_context
