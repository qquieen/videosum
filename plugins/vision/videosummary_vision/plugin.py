"""视觉插件主模块"""

import logging
from typing import List, Dict, Optional, Any
from pathlib import Path

from videosum.plugins.base import PluginBase, VisionPlugin as VisionPluginBase
from videosummary_vision.frame_extractor import FrameExtractor
from videosummary_vision.vlm_describer import VLMDescriber
from videosummary_vision.notes_generator import NotesGenerator

logger = logging.getLogger(__name__)


class VisionPlugin(VisionPluginBase):
    """视觉增强插件"""
    
    def __init__(self):
        self._frame_extractor: Optional[FrameExtractor] = None
        self._vlm_describer: Optional[VLMDescriber] = None
        self._notes_generator: Optional[NotesGenerator] = None
        self._initialized = False
    
    @property
    def name(self) -> str:
        return "videosummary-vision"
    
    @property
    def version(self) -> str:
        return "0.1.0"
    
    @property
    def description(self) -> str:
        return "视觉增强插件：关键帧提取、VLM描述、图文笔记生成"
    
    def install(self) -> bool:
        """安装插件依赖"""
        try:
            import subprocess
            import sys
            
            deps = ["opencv-python", "pillow"]
            for dep in deps:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", dep],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            
            logger.info("视觉插件依赖安装完成")
            return True
            
        except Exception as e:
            logger.error(f"安装依赖失败: {e}")
            return False
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化插件"""
        try:
            self._frame_extractor = FrameExtractor(
                frame_interval=config.get("frame_interval", 10),
                min_scene_change_threshold=config.get("min_scene_change_threshold", 30)
            )
            
            self._vlm_describer = VLMDescriber(
                model=config.get("vlm_model", "llava:7b")
            )
            
            self._notes_generator = NotesGenerator()
            
            self._initialized = True
            logger.info("视觉插件初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"初始化失败: {e}")
            return False
    
    def cleanup(self):
        """清理资源"""
        self._frame_extractor = None
        self._vlm_describer = None
        self._notes_generator = None
        self._initialized = False
        logger.info("视觉插件已清理")
    
    def extract_keyframes(self, video_path: str) -> List[Dict]:
        """
        提取关键帧
        
        Args:
            video_path: 视频文件路径
        
        Returns:
            关键帧列表 [{"path": str, "timestamp": float, "description": str}]
        """
        if not self._initialized or not self._frame_extractor:
            raise RuntimeError("插件未初始化")
        
        return self._frame_extractor.extract(video_path)
    
    def describe_frame(self, frame_path: str) -> str:
        """
        描述单帧内容
        
        Args:
            frame_path: 图片文件路径
        
        Returns:
            描述文本
        """
        if not self._initialized or not self._vlm_describer:
            raise RuntimeError("插件未初始化")
        
        return self._vlm_describer.describe(frame_path)
    
    def generate_notes(self, summary: str, frames: List[Dict]) -> str:
        """
        生成图文笔记
        
        Args:
            summary: 文本总结
            frames: 关键帧列表
        
        Returns:
            Markdown格式的图文笔记
        """
        if not self._initialized or not self._notes_generator:
            raise RuntimeError("插件未初始化")
        
        return self._notes_generator.generate(summary, frames)


def register() -> VisionPlugin:
    """注册插件（供插件管理器调用）"""
    return VisionPlugin()
