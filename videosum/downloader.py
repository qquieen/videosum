from pathlib import Path
from typing import Optional, Callable, Union
import logging
import subprocess
import json
import time
import shutil

from videosum.models import VideoMetadata

logger = logging.getLogger(__name__)

# 支持的媒体格式
SUPPORTED_VIDEO_FORMATS = ['.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv', '.wmv']
SUPPORTED_AUDIO_FORMATS = ['.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac', '.opus', '.wma']
SUPPORTED_FORMATS = SUPPORTED_VIDEO_FORMATS + SUPPORTED_AUDIO_FORMATS


class DownloadError(Exception):
    """下载错误"""
    pass


class InputHandler:
    """输入处理器（支持URL和本地文件）"""
    
    def __init__(self, temp_dir: str = "~/tmp/videosummary"):
        self.temp_dir = Path(temp_dir).expanduser()
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def is_url(self, input_str: str) -> bool:
        """判断输入是否为URL"""
        return input_str.startswith(('http://', 'https://', 'www.'))
    
    def is_local_file(self, input_str: str) -> bool:
        """判断输入是否为本地文件路径"""
        path = Path(input_str)
        return path.exists() and path.suffix.lower() in SUPPORTED_FORMATS
    
    def is_audio_file(self, file_path: Union[str, Path]) -> bool:
        """判断是否为音频文件"""
        return Path(file_path).suffix.lower() in SUPPORTED_AUDIO_FORMATS
    
    def is_video_file(self, file_path: Union[str, Path]) -> bool:
        """判断是否为视频文件"""
        return Path(file_path).suffix.lower() in SUPPORTED_VIDEO_FORMATS
    
    def process_local_file(
        self,
        file_path: str,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> tuple[VideoMetadata, Path]:
        """
        处理本地文件
        
        Args:
            file_path: 本地文件路径
            progress_callback: 进度回调
        
        Returns:
            (VideoMetadata, 音频文件路径)
        """
        path = Path(file_path).resolve()
        
        if not path.exists():
            raise DownloadError(f"文件不存在: {file_path}")
        
        if path.suffix.lower() not in SUPPORTED_FORMATS:
            raise DownloadError(f"不支持的格式: {path.suffix}")
        
        if progress_callback:
            progress_callback(0.1, f"处理本地文件: {path.name}")
        
        # 获取文件时长（使用ffprobe）
        duration = self._get_media_duration(str(path))
        
        # 如果是视频文件，提取音频；如果是音频文件，直接使用
        if self.is_video_file(path):
            if progress_callback:
                progress_callback(0.3, "从视频中提取音频...")
            audio_path = self._extract_audio_from_video(str(path), progress_callback)
        else:
            audio_path = path
        
        if progress_callback:
            progress_callback(1.0, f"文件处理完成: {path.name}")
        
        metadata = VideoMetadata(
            url=f"local://{path}",
            title=path.stem,
            duration=duration,
            uploader="本地文件",
            local_path=str(audio_path)
        )
        
        return metadata, audio_path
    
    def _get_media_duration(self, file_path: str) -> float:
        """使用ffprobe获取媒体时长"""
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                info = json.loads(result.stdout)
                return float(info.get("format", {}).get("duration", 0))
        except Exception:
            pass
        
        return 0.0
    
    def _extract_audio_from_video(
        self,
        video_path: str,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> Path:
        """从视频中提取音频"""
        video_file = Path(video_path)
        output_path = self.temp_dir / f"{video_file.stem}.mp3"
        
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vn",
            "-acodec", "libmp3lame",
            "-q:a", "0",
            "-y",
            str(output_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                raise DownloadError(f"音频提取失败: {result.stderr}")
            
            return output_path
            
        except subprocess.TimeoutExpired:
            raise DownloadError("音频提取超时")
    
    def copy_to_temp(self, file_path: str) -> Path:
        """复制文件到临时目录"""
        src = Path(file_path)
        dst = self.temp_dir / src.name
        shutil.copy2(src, dst)
        return dst


class VideoDownloader:
    """视频下载器（使用yt-dlp）"""
    
    def __init__(self, temp_dir: str = "~/tmp/videosummary"):
        self.temp_dir = Path(temp_dir).expanduser()
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.input_handler = InputHandler(temp_dir)
    
    def load(
        self,
        input_source: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        cookies_file: Optional[str] = None
    ) -> tuple[VideoMetadata, Path]:
        """
        统一入口：加载视频/音频（支持URL和本地文件）
        
        Args:
            input_source: URL或本地文件路径
            progress_callback: 进度回调
            cookies_file: cookies文件路径（仅URL模式）
        
        Returns:
            (VideoMetadata, 音频文件路径)
        """
        if self.input_handler.is_url(input_source):
            return self.download_audio(input_source, progress_callback, cookies_file)
        else:
            return self.input_handler.process_local_file(input_source, progress_callback)
    
    def _check_yt_dlp(self) -> bool:
        """检查yt-dlp是否安装"""
        try:
            result = subprocess.run(
                ["yt-dlp", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def download_audio(
        self,
        url: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        cookies_file: Optional[str] = None
    ) -> tuple[VideoMetadata, Path]:
        """
        下载音频（仅URL模式）
        """
        if not self._check_yt_dlp():
            raise DownloadError("yt-dlp未安装。请运行: pip install yt-dlp")
        
        if progress_callback:
            progress_callback(0.0, "获取视频信息...")
        
        # 获取视频信息
        metadata = self._get_video_info(url, cookies_file)
        
        if progress_callback:
            progress_callback(0.1, f"开始下载: {metadata.title}")
        
        # 下载音频
        audio_path = self._download_audio_stream(url, metadata, cookies_file, progress_callback)
        
        if progress_callback:
            progress_callback(1.0, f"下载完成: {audio_path.name}")
        
        metadata.local_path = str(audio_path)
        return metadata, audio_path
    
    def _get_video_info(
        self,
        url: str,
        cookies_file: Optional[str] = None
    ) -> VideoMetadata:
        """获取视频元数据"""
        cmd = [
            "yt-dlp",
            "--dump-json",
            "--no-download",
            url
        ]
        
        if cookies_file:
            cmd.extend(["--cookies", cookies_file])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                raise DownloadError(f"获取视频信息失败: {result.stderr}")
            
            info = json.loads(result.stdout)
            
            return VideoMetadata(
                url=url,
                title=info.get("title", "Unknown"),
                duration=info.get("duration", 0),
                uploader=info.get("uploader", "Unknown"),
                upload_date=info.get("upload_date"),
                thumbnail=info.get("thumbnail"),
            )
            
        except json.JSONDecodeError as e:
            raise DownloadError(f"解析视频信息失败: {e}")
        except subprocess.TimeoutExpired:
            raise DownloadError("获取视频信息超时")
    
    def _download_audio_stream(
        self,
        url: str,
        metadata: VideoMetadata,
        cookies_file: Optional[str],
        progress_callback: Optional[Callable[[float, str], None]]
    ) -> Path:
        """下载音频流"""
        output_dir = Path.home() / "tmp" / "videosummary"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_template = str(output_dir / f"{metadata.title}_%(id)s.%(ext)s")
        
        cmd = [
            "yt-dlp",
            "-x",  # 提取音频
            "--audio-format", "mp3",
            "--audio-quality", "0",  # 最佳质量
            "-o", output_template,
            "--no-playlist",
            url
        ]
        
        if cookies_file:
            cmd.extend(["--cookies", cookies_file])
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            stdout, stderr = process.communicate(timeout=600)
            
            if process.returncode != 0:
                raise DownloadError(f"下载失败: {stderr}")
            
            # 查找下载的文件
            for file in output_dir.iterdir():
                if metadata.title in file.name and file.suffix in ['.mp3', '.m4a', '.webm', '.opus']:
                    return file
            
            raise DownloadError("未找到下载的音频文件")
            
        except subprocess.TimeoutExpired:
            process.kill()
            raise DownloadError("下载超时")
    
    def download_video(
        self,
        url: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        cookies_file: Optional[str] = None
    ) -> tuple[VideoMetadata, Path]:
        """下载视频（用于视觉插件）"""
        if not self._check_yt_dlp():
            raise DownloadError("yt-dlp未安装")
        
        metadata = self._get_video_info(url, cookies_file)
        
        if progress_callback:
            progress_callback(0.1, f"开始下载视频: {metadata.title}")
        
        output_dir = Path.home() / "tmp" / "videosummary"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_template = str(output_dir / f"{metadata.title}_%(id)s.%(ext)s")
        
        cmd = [
            "yt-dlp",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "-o", output_template,
            "--no-playlist",
            url
        ]
        
        if cookies_file:
            cmd.extend(["--cookies", cookies_file])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
            
            if result.returncode != 0:
                raise DownloadError(f"下载视频失败: {result.stderr}")
            
            for file in output_dir.iterdir():
                if metadata.title in file.name and file.suffix in ['.mp4', '.mkv', '.webm']:
                    metadata.local_path = str(file)
                    return metadata, file
            
            raise DownloadError("未找到下载的视频文件")
            
        except subprocess.TimeoutExpired:
            raise DownloadError("下载视频超时")
