import asyncio
import uuid
import time
import logging
from typing import Callable, Optional, Dict, Any
from pathlib import Path

from videosum.models import (
    ProcessingTask, ProcessingStatus, VideoMetadata,
    TranscriptionResult, SummaryResult, SummaryChunk,
    CostEstimate, Language, LLMProvider, ASRProvider
)
from videosum.config_manager import ConfigManager
from videosum.downloader import InputHandler
from videosum.asr.local_whisper import LocalWhisperASR
from videosum.llm.unified_client import UnifiedLLMClient, PROVIDER_CONFIGS
from videosum.asr.base import ASREngine, ASRError
from videosum.llm.base import LLMEngine, LLMError

logger = logging.getLogger(__name__)


class SchedulerError(Exception):
    """调度器错误"""
    pass


class Scheduler:
    """核心调度器"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.tasks: Dict[str, ProcessingTask] = {}
        self._asr_engine: Optional[ASREngine] = None
        self._llm_engine: Optional[LLMEngine] = None
        self._input_handler = InputHandler(
            config_manager.get("app.temp_dir", "~/tmp/videosummary")
        )
    
    def _get_asr_engine(self) -> ASREngine:
        """获取ASR引擎（懒加载）"""
        if self._asr_engine is not None:
            return self._asr_engine
        
        asr_config = self.config.get_asr_config()
        backend = asr_config.get("backend", "local")
        
        if backend == "local":
            local_config = asr_config.get("local", {})
            self._asr_engine = LocalWhisperASR(
                model_size=local_config.get("model_size", "large-v3"),
                device=local_config.get("device", "auto"),
                compute_type=local_config.get("compute_type", "float16")
            )
        else:
            # 默认使用本地Whisper
            self._asr_engine = LocalWhisperASR()
        
        return self._asr_engine
    
    def _get_llm_engine(self) -> LLMEngine:
        """获取LLM引擎（懒加载）"""
        if self._llm_engine is not None:
            return self._llm_engine
        
        llm_config = self.config.get_llm_config()
        backend = llm_config.get("backend", "deepseek")
        
        # 映射后端名称到LLMProvider
        provider_map = {
            "openai": LLMProvider.OPENAI,
            "anthropic": LLMProvider.ANTHROPIC,
            "google": LLMProvider.GOOGLE,
            "deepseek": LLMProvider.DEEPSEEK,
            "qwen": LLMProvider.QWEN,
            "kimi": LLMProvider.KIMI,
            "glm": LLMProvider.GLM,
            "ollama": LLMProvider.OLLAMA,
        }
        
        provider = provider_map.get(backend, LLMProvider.DEEPSEEK)
        provider_config = llm_config.get(backend, {})
        
        api_key = provider_config.get("api_key", "")
        model = provider_config.get("model", "")
        
        self._llm_engine = UnifiedLLMClient(
            provider=provider,
            api_key=api_key,
            model=model,
            temperature=llm_config.get("temperature", 0.3),
            max_tokens=llm_config.get("max_tokens", 4000)
        )
        
        return self._llm_engine
    
    def create_task(self, input_source: str) -> str:
        """创建新任务"""
        task_id = str(uuid.uuid4())[:8]
        
        # 创建占位metadata
        metadata = VideoMetadata(
            url=input_source,
            title="加载中...",
            duration=0,
            uploader=""
        )
        
        task = ProcessingTask(
            task_id=task_id,
            video_metadata=metadata,
            status=ProcessingStatus.PENDING
        )
        
        self.tasks[task_id] = task
        return task_id
    
    def get_task(self, task_id: str) -> Optional[ProcessingTask]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def update_progress(
        self,
        task_id: str,
        status: ProcessingStatus,
        progress: float,
        step: str,
        error: Optional[str] = None
    ):
        """更新任务进度"""
        task = self.tasks.get(task_id)
        if task:
            task.status = status
            task.progress = progress
            task.current_step = step
            if error:
                task.error = error
            from datetime import datetime
            task.updated_at = datetime.now()
    
    async def process(
        self,
        task_id: str,
        input_source: str,
        output_language: Language = Language.CHINESE,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> ProcessingTask:
        """
        处理视频/音频
        
        Args:
            task_id: 任务ID
            input_source: URL或本地文件路径
            output_language: 输出语言
            progress_callback: 进度回调
        
        Returns:
            ProcessingTask: 处理结果
        """
        task = self.tasks.get(task_id)
        if not task:
            raise SchedulerError(f"任务不存在: {task_id}")
        
        task.output_language = output_language
        
        try:
            # 1. 下载/加载
            self.update_progress(task_id, ProcessingStatus.DOWNLOADING, 0.05, "正在加载...")
            
            def download_progress(p, msg):
                self.update_progress(task_id, ProcessingStatus.DOWNLOADING, 0.05 + p * 0.15, msg)
            
            metadata, audio_path = self._input_handler.load(
                input_source,
                progress_callback=download_progress
            )
            task.video_metadata = metadata
            
            # 2. ASR转写
            self.update_progress(task_id, ProcessingStatus.TRANSCRIBING, 0.20, "正在转写...")
            
            asr_engine = self._get_asr_engine()
            
            def transcribe_progress(p, msg):
                self.update_progress(task_id, ProcessingStatus.TRANSCRIBING, 0.20 + p * 0.40, msg)
            
            transcription = await asyncio.to_thread(
                asr_engine.transcribe,
                str(audio_path),
                transcribe_progress
            )
            task.transcription = transcription
            
            # 3. LLM总结
            self.update_progress(task_id, ProcessingStatus.SUMMARIZING, 0.60, "正在总结...")
            
            llm_engine = self._get_llm_engine()
            
            summary = await self._summarize(
                llm_engine,
                transcription,
                output_language,
                lambda p, msg: self.update_progress(
                    task_id, ProcessingStatus.SUMMARIZING, 0.60 + p * 0.35, msg
                )
            )
            task.summary = summary
            
            # 4. 计算费用
            task.cost = self._estimate_cost(transcription, summary)
            
            # 5. 完成
            self.update_progress(task_id, ProcessingStatus.COMPLETED, 1.0, "处理完成")
            
            return task
            
        except Exception as e:
            logger.error(f"处理失败: {str(e)}")
            self.update_progress(task_id, ProcessingStatus.FAILED, 0.0, "处理失败", str(e))
            raise
    
    async def _summarize(
        self,
        llm_engine: LLMEngine,
        transcription: TranscriptionResult,
        output_language: Language,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> SummaryResult:
        """生成总结"""
        start_time = time.time()
        
        # 构建完整文本
        full_text = "\n".join([s.text for s in transcription.segments])
        total_tokens = llm_engine.count_tokens(full_text)
        
        # 语言指令
        lang_instructions = {
            Language.CHINESE: "请使用中文输出。",
            Language.ENGLISH: "Please output in English.",
            Language.GERMAN: "Bitte geben Sie auf Deutsch aus.",
        }
        lang_instruction = lang_instructions.get(output_language, "")
        
        # 检查是否需要分块
        context_length = llm_engine.context_length
        
        if total_tokens < context_length - 1000:
            # 直接全文总结
            if progress_callback:
                progress_callback(0.5, "全文总结中...")
            
            summary = await self._summarize_full(
                llm_engine, transcription.segments, lang_instruction
            )
            chunks = []
        else:
            # 分块Map-Reduce
            if progress_callback:
                progress_callback(0.1, "文本较长，分块总结中...")
            
            chunks, summary = await self._summarize_chunked(
                llm_engine, transcription.segments, context_length,
                lang_instruction,
                lambda p, msg: progress_callback(0.1 + p * 0.8, msg) if progress_callback else None
            )
        
        # 提取关键点
        key_points = await self._extract_key_points(llm_engine, summary, lang_instruction)
        
        processing_time = time.time() - start_time
        
        return SummaryResult(
            full_summary=summary,
            chunks=chunks,
            key_points=key_points,
            total_tokens=total_tokens,
            provider=llm_engine.provider,
            processing_time=processing_time,
            language=output_language
        )
    
    async def _summarize_full(
        self,
        llm_engine: LLMEngine,
        segments: list,
        lang_instruction: str
    ) -> str:
        """全文总结"""
        # 构建带时间戳的文本
        text_with_time = []
        for seg in segments:
            minutes = int(seg.start // 60)
            seconds = int(seg.start % 60)
            text_with_time.append(f"[{minutes:02d}:{seconds:02d}] {seg.text}")
        
        full_text = "\n".join(text_with_time)
        
        messages = [
            {"role": "system", "content": f"""你是一个专业的视频内容总结助手。请根据以下转写文本生成结构化的总结。

要求：
1. {lang_instruction}
2. 保留关键时间点 [MM:SS]
3. 提取核心观点和要点
4. 使用Markdown格式输出
5. 结构清晰，分章节总结"""},
            {"role": "user", "content": f"请总结以下视频内容：\n\n{full_text}"}
        ]
        
        return await asyncio.to_thread(
            llm_engine.generate,
            messages,
            temperature=0.3
        )
    
    async def _summarize_chunked(
        self,
        llm_engine: LLMEngine,
        segments: list,
        context_length: int,
        lang_instruction: str,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> tuple:
        """分块Map-Reduce总结"""
        # 按时间窗口分割
        chunk_size = context_length - 500
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for seg in segments:
            seg_tokens = llm_engine.count_tokens(seg.text)
            if current_tokens + seg_tokens > chunk_size and current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                current_tokens = 0
            current_chunk.append(seg)
            current_tokens += seg_tokens
        
        if current_chunk:
            chunks.append(current_chunk)
        
        # 对每个块生成摘要
        chunk_summaries = []
        for i, chunk_segments in enumerate(chunks):
            if progress_callback:
                progress_callback(i / len(chunks), f"总结第 {i+1}/{len(chunks)} 块...")
            
            text_with_time = []
            for seg in chunk_segments:
                minutes = int(seg.start // 60)
                seconds = int(seg.start % 60)
                text_with_time.append(f"[{minutes:02d}:{seconds:02d}] {seg.text}")
            
            chunk_text = "\n".join(text_with_time)
            
            messages = [
                {"role": "system", "content": f"""你是一个视频内容总结助手。请为以下片段生成带时间戳的摘要。

要求：
1. {lang_instruction}
2. 格式：[时间] 摘要内容
3. 保留关键时间点
4. 提取核心观点"""},
                {"role": "user", "content": f"请总结以下片段：\n\n{chunk_text}"}
            ]
            
            chunk_summary = await asyncio.to_thread(
                llm_engine.generate,
                messages,
                temperature=0.3
            )
            
            chunk_summaries.append(SummaryChunk(
                chunk_index=i,
                time_start=chunk_segments[0].start,
                time_end=chunk_segments[-1].end,
                summary=chunk_summary,
                token_count=llm_engine.count_tokens(chunk_summary)
            ))
        
        # 合并所有块摘要，生成最终总结
        if progress_callback:
            progress_callback(0.9, "合并生成最终总结...")
        
        all_summaries = "\n\n".join([
            f"## 片段 {c.chunk_index + 1} ({c.time_start:.0f}s - {c.time_end:.0f}s)\n{c.summary}"
            for c in chunk_summaries
        ])
        
        messages = [
            {"role": "system", "content": f"""你是一个视频内容总结助手。以下是视频各个片段的摘要，请合并生成一个完整的结构化总结。

要求：
1. {lang_instruction}
2. 保留关键时间点
3. 去除重复内容
4. 使用Markdown格式输出
5. 结构清晰，分章节总结"""},
            {"role": "user", "content": f"请合并以下片段摘要：\n\n{all_summaries}"}
        ]
        
        final_summary = await asyncio.to_thread(
            llm_engine.generate,
            messages,
            temperature=0.3
        )
        
        return chunk_summaries, final_summary
    
    async def _extract_key_points(
        self,
        llm_engine: LLMEngine,
        summary: str,
        lang_instruction: str
    ) -> list:
        """提取关键点"""
        messages = [
            {"role": "system", "content": f"""请从以下总结中提取3-5个关键要点。

要求：
1. {lang_instruction}
2. 每个要点一行，使用"-"开头
3. 简洁明了"""},
            {"role": "user", "content": f"请提取关键要点：\n\n{summary}"}
        ]
        
        result = await asyncio.to_thread(
            llm_engine.generate,
            messages,
            temperature=0.3
        )
        
        # 解析关键点
        key_points = []
        for line in result.strip().split("\n"):
            line = line.strip()
            if line.startswith("-") or line.startswith("*"):
                key_points.append(line.lstrip("-* ").strip())
            elif line:
                key_points.append(line)
        
        return key_points[:5]
    
    def _estimate_cost(
        self,
        transcription: TranscriptionResult,
        summary: SummaryResult
    ) -> CostEstimate:
        """估算费用"""
        # ASR费用（本地免费）
        asr_cost = 0.0
        
        # LLM费用（简化计算）
        llm_cost = 0.0
        
        return CostEstimate(
            asr_cost=asr_cost,
            llm_cost=llm_cost,
            total_cost=asr_cost + llm_cost,
            token_count=summary.total_tokens,
            duration_hours=transcription.duration / 3600,
            currency="CNY"
        )
    
    async def qa(
        self,
        task_id: str,
        question: str
    ) -> str:
        """问答"""
        task = self.tasks.get(task_id)
        if not task or not task.transcription:
            raise SchedulerError("请先处理视频")
        
        llm_engine = self._get_llm_engine()
        
        # 构建上下文
        context_segments = task.transcription.segments[:20]  # 取前20个片段
        context = "\n".join([
            f"[{s.start:.0f}s] {s.text}" for s in context_segments
        ])
        
        messages = [
            {"role": "system", "content": f"""你是一个视频内容问答助手。请根据以下视频转写内容回答问题。

要求：
1. 基于视频内容回答
2. 如果信息不足，请说明
3. 引用相关时间点"""},
            {"role": "user", "content": f"视频内容：\n{context}\n\n问题：{question}"}
        ]
        
        answer = await asyncio.to_thread(
            llm_engine.generate,
            messages,
            temperature=0.3
        )
        
        return answer
