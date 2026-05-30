"""插件基类"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class PluginBase(ABC):
    """插件基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """插件名称"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """插件版本"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """插件描述"""
        pass
    
    @abstractmethod
    def install(self) -> bool:
        """安装插件依赖"""
        pass
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化插件"""
        pass
    
    @abstractmethod
    def cleanup(self):
        """清理资源"""
        pass


class VisionPlugin(PluginBase):
    """视觉插件接口"""
    
    @abstractmethod
    def extract_keyframes(self, video_path: str) -> List[Dict]:
        """
        提取关键帧
        
        Args:
            video_path: 视频文件路径
        
        Returns:
            关键帧列表 [{"path": str, "timestamp": float}]
        """
        pass
    
    @abstractmethod
    def describe_frame(self, frame_path: str) -> str:
        """
        描述单帧内容
        
        Args:
            frame_path: 图片文件路径
        
        Returns:
            描述文本
        """
        pass
    
    @abstractmethod
    def generate_notes(self, summary: str, frames: List[Dict]) -> str:
        """
        生成图文笔记
        
        Args:
            summary: 文本总结
            frames: 关键帧列表
        
        Returns:
            Markdown格式的图文笔记
        """
        pass
