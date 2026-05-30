from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Callable, AsyncIterator
import logging

from videosum.models import LLMProvider

logger = logging.getLogger(__name__)


class LLMEngine(ABC):
    """LLM引擎抽象基类"""
    
    @property
    @abstractmethod
    def provider(self) -> LLMProvider:
        """返回供应商类型"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """返回引擎名称"""
        pass
    
    @property
    @abstractmethod
    def context_length(self) -> int:
        """返回上下文长度"""
        pass
    
    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> str:
        """
        生成文本
        
        Args:
            messages: 消息列表，格式 [{"role": "user", "content": "..."}]
            temperature: 温度参数
            max_tokens: 最大token数
            stream: 是否流式输出
        
        Returns:
            生成的文本
        
        Raises:
            LLMError: 生成失败时抛出
        """
        pass
    
    @abstractmethod
    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: Optional[int] = None
    ) -> AsyncIterator[str]:
        """
        流式生成文本
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
        
        Yields:
            生成的文本片段
        """
        pass
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        计算文本的token数量
        
        Args:
            text: 输入文本
        
        Returns:
            token数量
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查引擎是否可用"""
        pass


class LLMError(Exception):
    """LLM相关错误"""
    pass
