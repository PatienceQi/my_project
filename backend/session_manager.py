"""
政策法规RAG问答系统 - 会话管理模块

提供多轮对话会话管理和上下文维护功能
"""

import uuid
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from backend.exceptions import SessionError


@dataclass
class Message:
    """消息对象"""
    role: str  # 'user' 或 'assistant'
    content: str
    timestamp: str
    entities: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.entities is None:
            self.entities = []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return asdict(self)


class ConversationSession:
    """对话会话对象"""
    
    def __init__(self, session_id: str, max_history: int = 10):
        """
        初始化对话会话
        
        Args:
            session_id: 会话唯一标识
            max_history: 最大历史消息数量
        """
        self.session_id = session_id
        self.created_at = datetime.now()
        self.last_activity = self.created_at
        self.messages: List[Message] = []
        self.max_history = max_history
        self.metadata: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def add_message(self, role: str, content: str, entities: List[Dict[str, Any]] = None):
        """
        添加消息到会话历史
        
        Args:
            role: 消息角色 ('user' 或 'assistant')
            content: 消息内容
            entities: 相关实体信息
        """
        with self._lock:
            message = Message(
                role=role,
                content=content,
                timestamp=datetime.now().isoformat(),
                entities=entities or []
            )
            
            self.messages.append(message)
            self.last_activity = datetime.now()
            
            # 保持历史记录在限制范围内
            if len(self.messages) > self.max_history * 2:
                # 保留最近的消息，但保持用户-助手对话完整性
                self.messages = self._trim_messages()
    
    def _trim_messages(self) -> List[Message]:
        """修剪消息列表，保持对话完整性"""
        if len(self.messages) <= self.max_history:
            return self.messages
        
        # 保留最近的消息，确保以用户消息开始
        recent_messages = self.messages[-self.max_history:]
        
        # 如果第一条消息是助手消息，尝试包含前一条用户消息
        if recent_messages and recent_messages[0].role == 'assistant':
            start_index = len(self.messages) - self.max_history - 1
            if start_index >= 0 and self.messages[start_index].role == 'user':
                recent_messages = [self.messages[start_index]] + recent_messages
        
        return recent_messages
    
    def get_context_for_llm(self, include_entities: bool = False) -> List[Dict[str, Any]]:
        """
        获取用于LLM的上下文消息
        
        Args:
            include_entities: 是否包含实体信息
            
        Returns:
            List[Dict[str, Any]]: LLM消息格式列表
        """
        with self._lock:
            # 获取最近6条消息用于上下文
            recent_messages = self.messages[-6:] if len(self.messages) > 6 else self.messages
            
            llm_messages = []
            for msg in recent_messages:
                message_dict = {
                    'role': msg.role,
                    'content': msg.content
                }
                
                if include_entities and msg.entities:
                    # 将实体信息作为附加上下文
                    entities_str = ', '.join([
                        f"{entity.get('label', '')}: {entity.get('name', '')}"
                        for entity in msg.entities
                    ])
                    if entities_str:
                        message_dict['content'] += f"\n[相关实体: {entities_str}]"
                
                llm_messages.append(message_dict)
            
            return llm_messages
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """获取对话摘要信息"""
        with self._lock:
            user_messages = [msg for msg in self.messages if msg.role == 'user']
            assistant_messages = [msg for msg in self.messages if msg.role == 'assistant']
            
            # 提取所有提到的实体
            all_entities = []
            for msg in self.messages:
                all_entities.extend(msg.entities)
            
            # 去重实体
            unique_entities = {}
            for entity in all_entities:
                key = f"{entity.get('label', '')}:{entity.get('name', '')}"
                if key not in unique_entities:
                    unique_entities[key] = entity
            
            return {
                'session_id': self.session_id,
                'created_at': self.created_at.isoformat(),
                'last_activity': self.last_activity.isoformat(),
                'total_messages': len(self.messages),
                'user_messages_count': len(user_messages),
                'assistant_messages_count': len(assistant_messages),
                'unique_entities_count': len(unique_entities),
                'entities': list(unique_entities.values()),
                'metadata': self.metadata
            }
    
    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """
        检查会话是否过期
        
        Args:
            timeout_minutes: 超时时间（分钟）
            
        Returns:
            bool: 是否过期
        """
        timeout_threshold = datetime.now() - timedelta(minutes=timeout_minutes)
        return self.last_activity < timeout_threshold
    
    def set_metadata(self, key: str, value: Any):
        """设置元数据"""
        with self._lock:
            self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """获取元数据"""
        return self.metadata.get(key, default)


class ConversationManager:
    """对话管理器"""
    
    def __init__(self, session_timeout_minutes: int = 30, max_sessions: int = 1000):
        """
        初始化对话管理器
        
        Args:
            session_timeout_minutes: 会话超时时间（分钟）
            max_sessions: 最大会话数量
        """
        self.session_timeout_minutes = session_timeout_minutes
        self.max_sessions = max_sessions
        self.sessions: Dict[str, ConversationSession] = {}
        self._lock = threading.RLock()
        self._cleanup_interval = 300  # 5分钟清理一次过期会话
        self._last_cleanup = datetime.now()
    
    def create_session(self, max_history: int = 10) -> str:
        """
        创建新的对话会话
        
        Args:
            max_history: 最大历史消息数量
            
        Returns:
            str: 会话ID
        """
        with self._lock:
            # 检查是否需要清理过期会话
            self._cleanup_expired_sessions()
            
            # 检查会话数量限制
            if len(self.sessions) >= self.max_sessions:
                self._force_cleanup_oldest_sessions()
            
            session_id = str(uuid.uuid4())
            self.sessions[session_id] = ConversationSession(session_id, max_history)
            
            return session_id
    
    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """
        获取指定会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            Optional[ConversationSession]: 会话对象，如果不存在或已过期则返回None
        """
        with self._lock:
            session = self.sessions.get(session_id)
            
            if session and session.is_expired(self.session_timeout_minutes):
                del self.sessions[session_id]
                return None
            
            return session
    
    def add_message_to_session(self, session_id: str, role: str, content: str, 
                              entities: List[Dict[str, Any]] = None) -> bool:
        """
        向会话添加消息
        
        Args:
            session_id: 会话ID
            role: 消息角色
            content: 消息内容
            entities: 相关实体
            
        Returns:
            bool: 添加是否成功
            
        Raises:
            SessionError: 当会话不存在或已过期时
        """
        session = self.get_session(session_id)
        if not session:
            raise SessionError(f"会话不存在或已过期: {session_id}", session_id)
        
        session.add_message(role, content, entities)
        return True
    
    def get_context_for_question(self, session_id: str, current_question: str, 
                                include_entities: bool = False) -> str:
        """
        获取包含上下文的完整问题
        
        Args:
            session_id: 会话ID
            current_question: 当前问题
            include_entities: 是否包含实体信息
            
        Returns:
            str: 包含上下文的问题
        """
        session = self.get_session(session_id)
        if not session:
            return current_question
        
        context_messages = session.get_context_for_llm(include_entities)
        if not context_messages:
            return current_question
        
        # 构建上下文提示
        context_prompt = "根据以下对话历史，回答用户的新问题：\n\n"
        context_prompt += "对话历史：\n"
        
        for msg in context_messages:
            role_name = "用户" if msg['role'] == 'user' else "助手"
            context_prompt += f"{role_name}: {msg['content']}\n"
        
        context_prompt += f"\n当前问题: {current_question}"
        context_prompt += "\n\n请基于对话历史的上下文来理解和回答当前问题。"
        
        return context_prompt
    
    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话摘要
        
        Args:
            session_id: 会话ID
            
        Returns:
            Optional[Dict[str, Any]]: 会话摘要，如果会话不存在则返回None
        """
        session = self.get_session(session_id)
        if not session:
            return None
        
        return session.get_conversation_summary()
    
    def list_active_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        列出活跃会话
        
        Args:
            limit: 返回数量限制
            
        Returns:
            List[Dict[str, Any]]: 会话摘要列表
        """
        with self._lock:
            # 按最后活动时间排序
            sorted_sessions = sorted(
                self.sessions.values(),
                key=lambda s: s.last_activity,
                reverse=True
            )
            
            summaries = []
            for session in sorted_sessions[:limit]:
                if not session.is_expired(self.session_timeout_minutes):
                    summaries.append(session.get_conversation_summary())
            
            return summaries
    
    def delete_session(self, session_id: str) -> bool:
        """
        删除指定会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            bool: 删除是否成功
        """
        with self._lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                return True
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取管理器统计信息"""
        with self._lock:
            active_sessions = [
                s for s in self.sessions.values()
                if not s.is_expired(self.session_timeout_minutes)
            ]
            
            total_messages = sum(len(s.messages) for s in active_sessions)
            
            return {
                'total_sessions': len(self.sessions),
                'active_sessions': len(active_sessions),
                'expired_sessions': len(self.sessions) - len(active_sessions),
                'total_messages': total_messages,
                'average_messages_per_session': total_messages / len(active_sessions) if active_sessions else 0,
                'session_timeout_minutes': self.session_timeout_minutes,
                'max_sessions': self.max_sessions,
                'last_cleanup': self._last_cleanup.isoformat()
            }
    
    def _cleanup_expired_sessions(self):
        """清理过期会话"""
        now = datetime.now()
        if now - self._last_cleanup < timedelta(seconds=self._cleanup_interval):
            return
        
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if session.is_expired(self.session_timeout_minutes)
        ]
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
        
        self._last_cleanup = now
    
    def _force_cleanup_oldest_sessions(self):
        """强制清理最老的会话以释放空间"""
        if len(self.sessions) < self.max_sessions:
            return
        
        # 按最后活动时间排序，删除最老的25%会话
        sorted_sessions = sorted(
            self.sessions.items(),
            key=lambda item: item[1].last_activity
        )
        
        sessions_to_remove = int(len(sorted_sessions) * 0.25)
        for session_id, _ in sorted_sessions[:sessions_to_remove]:
            del self.sessions[session_id]


# 全局会话管理器实例
conversation_manager = ConversationManager()


def get_conversation_manager() -> ConversationManager:
    """获取全局会话管理器实例"""
    return conversation_manager