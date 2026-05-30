from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class Language(Enum):
    """支持的语言"""
    CHINESE = "zh"
    ENGLISH = "en"
    GERMAN = "de"


class LLMProvider(Enum):
    """LLM供应商"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    DEEPSEEK = "deepseek"
    QWEN = "qwen"
    KIMI = "kimi"
    GLM = "glm"
    OLLAMA = "ollama"


class ASRProvider(Enum):
    """ASR供应商"""
    LOCAL_WHISPER = "local_whisper"
    OPENAI_WHISPER = "openai_whisper"
    ALIYUN = "aliyun"
    GOOGLE = "google"


class ProcessingStatus(Enum):
    """处理状态"""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    TRANSCRIBING = "transcribing"
    SUMMARIZING = "summarizing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Segment:
    """ASR转写片段"""
    start: float
    end: float
    text: str
    confidence: float = 1.0
    language: str = "auto"


@dataclass
class VideoMetadata:
    """视频元数据"""
    url: str
    title: str
    duration: float
    uploader: str
    upload_date: Optional[str] = None
    thumbnail: Optional[str] = None
    local_path: Optional[str] = None
    detected_language: str = "auto"


@dataclass
class TranscriptionResult:
    """ASR转写结果"""
    segments: List[Segment]
    language: str
    duration: float
    provider: ASRProvider
    processing_time: float


@dataclass
class SummaryChunk:
    """分块摘要"""
    chunk_index: int
    time_start: float
    time_end: float
    summary: str
    token_count: int


@dataclass
class SummaryResult:
    """最终摘要结果"""
    full_summary: str
    chunks: List[SummaryChunk]
    key_points: List[str]
    total_tokens: int
    provider: LLMProvider
    processing_time: float
    language: Language


@dataclass
class QAExchange:
    """问答交互"""
    question: str
    answer: str
    source_segments: List[Segment]
    timestamp: float
    language: Language


@dataclass
class CostEstimate:
    """费用估算"""
    asr_cost: float
    llm_cost: float
    total_cost: float
    token_count: int
    duration_hours: float
    currency: str = "CNY"


@dataclass
class ProcessingTask:
    """处理任务状态"""
    task_id: str
    video_metadata: VideoMetadata
    status: ProcessingStatus
    progress: float = 0.0
    current_step: str = ""
    input_language: Language = Language.CHINESE
    output_language: Language = Language.CHINESE
    transcription: Optional[TranscriptionResult] = None
    summary: Optional[SummaryResult] = None
    qa_history: List[QAExchange] = field(default_factory=list)
    cost: Optional[CostEstimate] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
