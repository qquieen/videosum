import asyncio
import uuid
import time
import logging
import json
import threading
from typing import Callable, Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

from videosum.models import (
    ProcessingTask, ProcessingStatus, VideoMetadata,
    TranscriptionResult, SummaryResult, SummaryChunk,
    CostEstimate, Language, LLMProvider, ASRProvider, QAExchange
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
    """
    核心调度器
    
    线程安全设计：
    - self._tasks_lock: 保护 self.tasks 字典的读写
    - self._engine_lock: 保护 ASR/LLM 引擎的懒加载
    - save_task 使用原子写入（先写临时文件再重命名）
    """
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        
        # 线程锁
        self._tasks_lock = threading.Lock()
        self._engine_lock = threading.Lock()
        
        # 任务存储
        self.tasks: Dict[str, ProcessingTask] = {}
        
        # 引擎实例（懒加载）
        self._asr_engine: Optional[ASREngine] = None
        self._llm_engine: Optional[LLMEngine] = None
        
        # 输入处理器
        self._input_handler = InputHandler(
            config_manager.get("app.temp_dir", "~/tmp/videosummary")
        )
        
        # 缓存目录
        self.cache_dir = Path(
            config_manager.get("app.temp_dir", "~/tmp/videosummary")
        ).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 启动时加载所有任务
        self._load_all_tasks()

    def _load_all_tasks(self):
        """从磁盘加载所有缓存的任务"""
        try:
            for task_dir in self.cache_dir.iterdir():
                if task_dir.is_dir():
                    state_file = task_dir / "state.json"
                    if state_file.exists():
                        try:
                            with open(state_file, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                task = ProcessingTask.from_dict(data)
                                with self._tasks_lock:
                                    self.tasks[task.task_id] = task
                        except Exception as e:
                            logger.warning(f"加载任务失败 {task_dir.name}: {e}")
        except Exception as e:
            logger.error(f"加载任务目录失败: {e}")

    def save_task(self, task_id: str):
        """
        将任务持久化到磁盘（原子写入）
        
        原子写入流程：
        1. 写入临时文件 state.json.tmp
        2. 重命名为 state.json
        这样可以防止写入过程中断导致文件损坏
        """
        with self._tasks_lock:
            task = self.tasks.get(task_id)
            if not task:
                return
        
        task_dir = self.cache_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        state_file = task_dir / "state.json"
        temp_file = task_dir / "state.json.tmp"
        
        try:
            # 原子写入
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(task.to_json())
            
            # 重命名（原子操作）
            temp_file.replace(state_file)
        except Exception as e:
            logger.error(f"保存任务状态失败 {task_id}: {e}")
            # 清理临时文件
            if temp_file.exists():
                temp_file.unlink()

    def _get_asr_engine(self) -> ASREngine:
        """获取ASR引擎（懒加载，线程安全）"""
        if self._asr_engine is not None:
            return self._asr_engine
        
        with self._engine_lock:
            # 双重检查
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
                # TODO: 实现 OpenAI/Aliyun ASR 适配器
                self._asr_engine = LocalWhisperASR()
            
            return self._asr_engine
    
    def _get_llm_engine(self) -> LLMEngine:
        """获取LLM引擎（懒加载，线程安全）"""
        if self._llm_engine is not None:
            return self._llm_engine
        
        with self._engine_lock:
            # 双重检查
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
        """创建新任务（线程安全）"""
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
        
        with self._tasks_lock:
            self.tasks[task_id] = task
        
        # 立即持久化
        self.save_task(task_id)
        
        return task_id
    
    def get_task(self, task_id: str) -> Optional[ProcessingTask]:
        """获取任务（线程安全）"""
        with self._tasks_lock:
            return self.tasks.get(task_id)
    
    def list_tasks(self) -> List[ProcessingTask]:
        """列出所有任务（线程安全）"""
        with self._tasks_lock:
            return list(self.tasks.values())
    
    def delete_task(self, task_id: str) -> bool:
        """删除任务（线程安全）"""
        with self._tasks_lock:
            if task_id not in self.tasks:
                return False
            del self.tasks[task_id]
        
        # 删除磁盘文件
        task_dir = self.cache_dir / task_id
        if task_dir.exists():
            import shutil
            shutil.rmtree(task_dir, ignore_errors=True)
        
        return True
    
    def update_progress(
        self,
        task_id: str,
        status: ProcessingStatus,
        progress: float,
        step: str,
        error: Optional[str] = None
    ):
        """更新任务进度并持久化（线程安全）"""
        with self._tasks_lock:
            task = self.tasks.get(task_id)
            if not task:
                return
            
            task.status = status
            task.progress = progress
            task.current_step = step
            if error:
                task.error = error
            task.updated_at = datetime.now()
        
        # 持久化（在锁外执行，避免长时间持锁）
        self.save_task(task_id)

    async def process(
        self,
        task_id: str,
        input_source: str,
        output_language: Language = Language.CHINESE,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> ProcessingTask:
        """
        处理视频/音频 (支持断点续传，线程安全)
        """
        task = self.get_task(task_id)
        if not task:
            raise SchedulerError(f"任务不存在: {task_id}")
        
        task.output_language = output_language
        
        try:
            # 1. 下载/加载 (仅当尚未下载或元数据缺失时执行)
            if not task.video_metadata or task.video_metadata.duration == 0:
                self.update_progress(task_id, ProcessingStatus.DOWNLOADING, 0.05, "正在加载...")
                def download_progress(p, msg):
                    self.update_progress(task_id, ProcessingStatus.DOWNLOADING, 0.05 + p * 0.15, msg)
                
                metadata, audio_path = self._input_handler.load(
                    input_source,
                    progress_callback=download_progress
                )
                task.video_metadata = metadata
                self.save_task(task_id)
            
            # 2. ASR转写 (仅当尚未转写时执行)
            if not task.transcription:
                self.update_progress(task_id, ProcessingStatus.TRANSCRIBING, 0.20, "正在转写...")
                asr_engine = self._get_asr_engine()
                
                def transcribe_progress(p, msg):
                    self.update_progress(task_id, ProcessingStatus.TRANSCRIBING, 0.20 + p * 0.40, msg)
                
                audio_path = task.video_metadata.local_path
                transcription = await asyncio.to_thread(
                    asr_engine.transcribe,
                    str(audio_path),
                    transcribe_progress
                )
                task.transcription = transcription
                self.save_task(task_id)
            
            # 3. LLM总结 (仅当尚未生成总结时执行)
            if not task.summary:
                self.update_progress(task_id, ProcessingStatus.SUMMARIZING, 0.60, "正在总结...")
                llm_engine = self._get_llm_engine()
                
                summary = await self._summarize(
                    llm_engine,
                    task.transcription,
                    output_language,
                    lambda p, msg: self.update_progress(
                        task_id, ProcessingStatus.SUMMARIZING, 0.60 + p * 0.35, msg
                    )
                )
                task.summary = summary
                self.save_task(task_id)
            
            # 4. 计算费用
            if not task.cost:
                task.cost = self._estimate_cost(task.transcription, task.summary)
                self.save_task(task_id)
            
            # 5. 完成
            self.update_progress(task_id, ProcessingStatus.COMPLETED, 1.0, "处理完成")
            return task
            
        except Exception as e:
            logger.error(f"处理失败: {str(e)}")
            self.update_progress(task_id, ProcessingStatus.FAILED, task.progress, "处理失败", str(e))
            raise
    
    async def _summarize(
        self,
        llm_engine: LLMEngine,
        transcription: TranscriptionResult,
        output_language: Language,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> SummaryResult:
        """生成总结 (递归策略)"""
        start_time = time.time()
        
        # 1. 准备初始文本
        text_with_time = []
        for seg in transcription.segments:
            minutes = int(seg.start // 60)
            seconds = int(seg.start % 60)
            text_with_time.append(f"[{minutes:02d}:{seconds:02d}] {seg.text}")
        
        # 2. 语言指令
        lang_instructions = {
            Language.CHINESE: "请使用中文输出。",
            Language.ENGLISH: "Please output in English.",
            Language.GERMAN: "Bitte geben Sie auf Deutsch aus.",
        }
        lang_instruction = lang_instructions.get(output_language, "")
        
        # 3. 递归总结逻辑
        context_limit = llm_engine.context_length - 1000
        
        async def recursive_summarize_step(texts: List[str], depth: int = 0) -> str:
            combined_text = "\n\n".join(texts)
            if llm_engine.count_tokens(combined_text) < context_limit:
                if progress_callback:
                    progress_callback(0.9, f"正在生成最终总结 (层级 {depth})...")
                
                messages = [
                    {"role": "system", "content": f"你是一个专业的视频总结专家。请根据提供的视频片段摘要，生成一个结构化的、排版精美的Markdown总结。要求：1. {lang_instruction} 2. 包含核心观点、关键时刻、结论。3. 结构清晰。"},
                    {"role": "user", "content": f"内容如下：\n\n{combined_text}"}
                ]
                return await asyncio.to_thread(llm_engine.generate, messages)

            # 需要进一步分块
            if progress_callback:
                progress_callback(0.1 + depth * 0.2, f"文本较长，正在进行第 {depth + 1} 层递归总结...")
            
            new_summaries = []
            current_batch = []
            current_tokens = 0
            
            for t in texts:
                t_tokens = llm_engine.count_tokens(t)
                if current_tokens + t_tokens > context_limit and current_batch:
                    # 处理当前批次
                    batch_text = "\n\n".join(current_batch)
                    messages = [
                        {"role": "system", "content": f"请为以下视频片段生成简明扼要的摘要。要求：1. {lang_instruction} 2. 保留关键时间点 [MM:SS]。3. 突出核心信息。"},
                        {"role": "user", "content": batch_text}
                    ]
                    summary = await asyncio.to_thread(llm_engine.generate, messages)
                    new_summaries.append(summary)
                    current_batch = []
                    current_tokens = 0
                
                current_batch.append(t)
                current_tokens += t_tokens
            
            if current_batch:
                batch_text = "\n\n".join(current_batch)
                messages = [
                    {"role": "system", "content": f"请为以下视频片段生成简明扼要的摘要。要求：1. {lang_instruction} 2. 保留关键时间点 [MM:SS]。3. 突出核心信息。"},
                    {"role": "user", "content": batch_text}
                ]
                summary = await asyncio.to_thread(llm_engine.generate, messages)
                new_summaries.append(summary)
            
            return await recursive_summarize_step(new_summaries, depth + 1)

        # 执行递归
        final_summary = await recursive_summarize_step(text_with_time)
        
        # 4. 提取关键点
        key_points = await self._extract_key_points(llm_engine, final_summary, lang_instruction)
        
        processing_time = time.time() - start_time
        return SummaryResult(
            full_summary=final_summary,
            chunks=[],
            key_points=key_points,
            total_tokens=llm_engine.count_tokens(final_summary),
            provider=llm_engine.provider,
            processing_time=processing_time,
            language=output_language
        )
    
    async def qa(
        self,
        task_id: str,
        question: str
    ) -> str:
        """问答 (接入向量检索预留)"""
        task = self.get_task(task_id)
        if not task or not task.transcription:
            raise SchedulerError("请先处理视频")
        
        llm_engine = self._get_llm_engine()
        
        # 1. 获取上下文
        context_segments = self._get_context_via_rag(task, question)
        
        context = "\n".join([
            f"[{s.start:.0f}s] {s.text}" for s in context_segments
        ])
        
        # 2. 调用 LLM
        lang_instruction = "请使用与问题相同的语言回答。"
        messages = [
            {"role": "system", "content": f"""你是一个视频内容问答助手。请根据以下视频转写内容回答问题。要求：1. 严谨、准确，基于提供的视频内容。2. 如果视频中没提到，请直说。3. 引用具体的时间点。4. {lang_instruction}"""},
            {"role": "user", "content": f"视频内容转写：\n{context}\n\n问题：{question}"}
        ]
        
        answer = await asyncio.to_thread(llm_engine.generate, messages)
        
        # 3. 记录历史
        qa_exchange = QAExchange(
            question=question,
            answer=answer,
            source_segments=context_segments,
            timestamp=time.time(),
            language=Language.CHINESE
        )
        
        with self._tasks_lock:
            task.qa_history.append(qa_exchange)
        
        self.save_task(task_id)
        
        return answer

    def _get_context_via_rag(self, task: ProcessingTask, question: str, k: int = 10) -> list:
        """简单的上下文获取逻辑 (向量搜索实现前的过渡)"""
        segments = task.transcription.segments
        if len(segments) <= 20:
            return segments
        
        # 简单的关键词匹配排序
        keywords = question.split()
        scored_segments = []
        for seg in segments:
            score = sum(1 for kw in keywords if kw.lower() in seg.text.lower())
            scored_segments.append((score, seg))
        
        scored_segments.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored_segments[:k]]

    async def _extract_key_points(
        self,
        llm_engine: LLMEngine,
        summary: str,
        lang_instruction: str
    ) -> list:
        """提取关键点"""
        messages = [
            {"role": "system", "content": f"请从以下视频总结中提取3-5个最核心的关键要点。要求：1. {lang_instruction} 2. 每个要点一行，使用'-'开头。3. 简洁有力。"},
            {"role": "user", "content": f"总结如下：\n\n{summary}"}
        ]
        
        result = await asyncio.to_thread(llm_engine.generate, messages)
        
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
        """估算费用 (ASR+LLM)"""
        return CostEstimate(
            asr_cost=0.0,
            llm_cost=0.0,
            total_cost=0.0,
            token_count=summary.total_tokens,
            duration_hours=transcription.duration / 3600,
            currency="CNY"
        )
