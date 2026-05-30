from typing import Callable, Optional
import time
import logging

from videosum.models import Segment, TranscriptionResult, ASRProvider
from videosum.asr.base import ASREngine, ASRError

logger = logging.getLogger(__name__)


class LocalWhisperASR(ASREngine):
    """本地Whisper ASR引擎（使用faster_whisper）"""
    
    def __init__(
        self,
        model_size: str = "large-v3",
        device: str = "auto",
        compute_type: str = "float16"
    ):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None
    
    @property
    def provider(self) -> ASRProvider:
        return ASRProvider.LOCAL_WHISPER
    
    @property
    def name(self) -> str:
        return f"Local Whisper ({self.model_size})"
    
    def _load_model(self):
        """懒加载模型"""
        if self._model is not None:
            return
        
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise ASRError(
                "faster_whisper未安装。请运行: pip install faster-whisper"
            )
        
        logger.info(f"加载Whisper模型: {self.model_size}, 设备: {self.device}")
        self._model = WhisperModel(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type
        )
    
    def transcribe(
        self,
        audio_path: str,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> TranscriptionResult:
        """转写音频文件"""
        self._load_model()
        
        if progress_callback:
            progress_callback(0.0, "开始转写...")
        
        start_time = time.time()
        
        try:
            segments_gen, info = self._model.transcribe(
                audio_path,
                beam_size=5,
                language=None,  # 自动检测语言
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=200
                )
            )
            
            detected_language = info.language
            duration = info.duration
            
            if progress_callback:
                progress_callback(0.1, f"检测到语言: {detected_language}")
            
            segments = []
            for i, seg in enumerate(segments_gen):
                segments.append(Segment(
                    start=seg.start,
                    end=seg.end,
                    text=seg.text.strip(),
                    confidence=seg.avg_logprob,
                    language=detected_language
                ))
                
                if progress_callback and duration > 0:
                    progress = 0.1 + 0.9 * (seg.end / duration)
                    progress_callback(min(progress, 1.0), f"转写中... {seg.end:.1f}s")
            
            processing_time = time.time() - start_time
            
            if progress_callback:
                progress_callback(1.0, f"转写完成，耗时 {processing_time:.1f}s")
            
            return TranscriptionResult(
                segments=segments,
                language=detected_language,
                duration=duration,
                provider=self.provider,
                processing_time=processing_time
            )
            
        except Exception as e:
            raise ASRError(f"转写失败: {str(e)}")
    
    def is_available(self) -> bool:
        """检查是否可用"""
        try:
            from faster_whisper import WhisperModel
            return True
        except ImportError:
            return False
