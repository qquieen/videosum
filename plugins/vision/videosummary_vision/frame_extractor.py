"""关键帧提取模块"""

import logging
from typing import List, Dict, Optional
from pathlib import Path
import subprocess
import json

logger = logging.getLogger(__name__)


class FrameExtractorError(Exception):
    """关键帧提取错误"""
    pass


class FrameExtractor:
    """关键帧提取器"""
    
    def __init__(
        self,
        frame_interval: int = 10,
        min_scene_change_threshold: int = 30
    ):
        """
        初始化
        
        Args:
            frame_interval: 等间隔提取的间隔（秒）
            min_scene_change_threshold: 场景变化检测阈值
        """
        self.frame_interval = frame_interval
        self.min_scene_change_threshold = min_scene_change_threshold
    
    def extract(
        self,
        video_path: str,
        output_dir: Optional[str] = None
    ) -> List[Dict]:
        """
        提取关键帧
        
        Args:
            video_path: 视频文件路径
            output_dir: 输出目录（默认在视频同目录下创建frames文件夹）
        
        Returns:
            关键帧列表 [{"path": str, "timestamp": float}]
        """
        video_file = Path(video_path)
        
        if not video_file.exists():
            raise FrameExtractorError(f"视频文件不存在: {video_path}")
        
        # 设置输出目录
        if output_dir:
            out_dir = Path(output_dir)
        else:
            out_dir = video_file.parent / f"{video_file.stem}_frames"
        
        out_dir.mkdir(parents=True, exist_ok=True)
        
        frames = []
        
        # 方法1: 等间隔提取
        interval_frames = self._extract_by_interval(video_path, out_dir)
        frames.extend(interval_frames)
        
        # 方法2: 场景变化检测
        scene_frames = self._extract_by_scene_change(video_path, out_dir)
        frames.extend(scene_frames)
        
        # 去重并按时间排序
        frames = self._deduplicate_frames(frames)
        frames.sort(key=lambda x: x["timestamp"])
        
        logger.info(f"提取了 {len(frames)} 个关键帧")
        return frames
    
    def _extract_by_interval(
        self,
        video_path: str,
        output_dir: Path
    ) -> List[Dict]:
        """等间隔提取"""
        frames = []
        
        # 获取视频时长
        duration = self._get_video_duration(video_path)
        if duration <= 0:
            return frames
        
        # 计算时间点
        timestamps = []
        t = 0
        while t < duration:
            timestamps.append(t)
            t += self.frame_interval
        
        # 提取每个时间点的帧
        for i, ts in enumerate(timestamps):
            output_path = output_dir / f"interval_{i:04d}_{ts:.0f}s.jpg"
            
            cmd = [
                "ffmpeg",
                "-ss", str(ts),
                "-i", video_path,
                "-vframes", "1",
                "-q:v", "2",
                "-y",
                str(output_path)
            ]
            
            try:
                subprocess.run(cmd, capture_output=True, timeout=10)
                
                if output_path.exists():
                    frames.append({
                        "path": str(output_path),
                        "timestamp": ts,
                        "type": "interval"
                    })
            except Exception as e:
                logger.warning(f"提取帧失败 {ts}s: {e}")
        
        return frames
    
    def _extract_by_scene_change(
        self,
        video_path: str,
        output_dir: Path
    ) -> List[Dict]:
        """场景变化检测提取"""
        frames = []
        
        # 使用ffprobe检测场景变化
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-show_entries", "frame=pts_time",
            "-f", "lavfi",
            "-i", f"movie={video_path},select='gt(scene\\,{self.min_scene_change_threshold/100})'",
            "-of", "json"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                scene_changes = data.get("frames", [])
                
                for i, frame in enumerate(scene_changes):
                    ts = float(frame.get("pts_time", 0))
                    output_path = output_dir / f"scene_{i:04d}_{ts:.0f}s.jpg"
                    
                    extract_cmd = [
                        "ffmpeg",
                        "-ss", str(ts),
                        "-i", video_path,
                        "-vframes", "1",
                        "-q:v", "2",
                        "-y",
                        str(output_path)
                    ]
                    
                    subprocess.run(extract_cmd, capture_output=True, timeout=10)
                    
                    if output_path.exists():
                        frames.append({
                            "path": str(output_path),
                            "timestamp": ts,
                            "type": "scene_change"
                        })
                        
        except Exception as e:
            logger.warning(f"场景检测失败: {e}")
        
        return frames
    
    def _get_video_duration(self, video_path: str) -> float:
        """获取视频时长"""
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            video_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return float(data.get("format", {}).get("duration", 0))
        except Exception:
            pass
        
        return 0.0
    
    def _deduplicate_frames(self, frames: List[Dict]) -> List[Dict]:
        """去重（时间相近的帧只保留一个）"""
        if not frames:
            return []
        
        deduplicated = [frames[0]]
        
        for frame in frames[1:]:
            # 如果与最后一个保留的帧时间差大于2秒，则保留
            if frame["timestamp"] - deduplicated[-1]["timestamp"] > 2:
                deduplicated.append(frame)
        
        return deduplicated
