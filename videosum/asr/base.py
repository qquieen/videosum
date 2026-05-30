from abc import ABC, abstractmethod
from typing import Callable, Optional, List
import logging

from videosum.models import Segment, TranscriptionResult, ASRProvider

logger = logging.getLogger(__name__)


class ASREngine(ABC):
    """ASR引擎抽象基类"""
    
    @property
    @abstractmethod
    def provider(self) -> ASRProvider:
        """返回供应商类型"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """返回引擎名称"""
        pass
    
    @abstractmethod
    def transcribe(
        self, 
        audio_path: str, 
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> TranscriptionResult:
        """
        转写音频文件
        
        Args:
            audio_path: 音频文件路径
            progress_callback: 进度回调函数 (progress: 0-1, message: str)
        
        Returns:
            TranscriptionResult: 转写结果
        
        Raises:
            ASRError: 转写失败时抛出
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查引擎是否可用"""
        pass


class ASRError(Exception):
    """ASR相关错误"""
    pass
