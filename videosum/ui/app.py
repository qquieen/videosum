import gradio as gr
import asyncio
from typing import Optional
import logging

from videosum.config_manager import ConfigManager
from videosum.scheduler import Scheduler
from videosum.models import Language, ProcessingStatus
from videosum.i18n import I18nManager

logger = logging.getLogger(__name__)


class VideoSumUI:
    """VideoSum Gradio界面"""
    
    def __init__(self):
        self.config = ConfigManager()
        self.scheduler = Scheduler(self.config)
        self.i18n = I18nManager(self.config.get("app.language", "zh"))
        self.current_task_id: Optional[str] = None
    
    def create_ui(self) -> gr.Blocks:
        """创建Gradio界面"""
        
        with gr.Blocks(title="VideoSum") as app:
            gr.Markdown("# VideoSum - 本地智能视频总结工具")
            
            with gr.Row():
                with gr.Column(scale=1):
                    self._create_input_panel()
                
                with gr.Column(scale=2):
                    self._create_output_panel()
            
            self._create_status_bar()
            self._setup_events()
        
        return app
    
    def _create_input_panel(self):
        with gr.Group():
            gr.Markdown("### 输入")
            
            self.url_input = gr.Textbox(
                label="视频URL或本地文件路径",
                placeholder="输入B站、YouTube链接，或本地文件路径...",
                lines=2
            )
            
            self.file_input = gr.File(
                label="或上传文件",
                file_types=["video", "audio"],
            )
            
            self.output_language = gr.Radio(
                label="输出语言",
                choices=["中文", "English", "Deutsch"],
                value="中文"
            )
            
            self.backend_mode = gr.Radio(
                label="后端模式",
                choices=["推荐", "纯本地", "纯云端"],
                value="推荐"
            )
            
            self.start_btn = gr.Button(
                "开始总结",
                variant="primary",
                size="lg"
            )
            
            self.progress_bar = gr.Slider(
                label="进度",
                minimum=0,
                maximum=100,
                value=0,
                interactive=False
            )
            
            self.status_text = gr.Textbox(
                label="状态",
                value="就绪",
                interactive=False
            )
    
    def _create_output_panel(self):
        with gr.Tabs():
            with gr.Tab("总结结果"):
                self.summary_output = gr.Markdown(
                    value="*暂无总结，请先处理视频*"
                )
                with gr.Row():
                    self.copy_btn = gr.Button("复制")
                    self.export_btn = gr.Button("导出")
            
            with gr.Tab("问答助手"):
                self.chatbot = gr.Chatbot(
                    label="问答对话",
                    height=400
                )
                with gr.Row():
                    self.qa_input = gr.Textbox(
                        label="输入问题",
                        placeholder="基于视频内容提问...",
                        scale=4
                    )
                    self.qa_btn = gr.Button("发送", scale=1)
            
            with gr.Tab("课件预览"):
                gr.Markdown("*课件生成功能开发中...*")
    
    def _create_status_bar(self):
        with gr.Row():
            gr.Markdown("**当前配置**：ASR=本地Whisper | LLM=DeepSeek | 语言=中文")
            self.cost_display = gr.Markdown("**预估费用**：¥0.00")
    
    def _setup_events(self):
        self.file_input.change(
            fn=self._on_file_upload,
            inputs=[self.file_input],
            outputs=[self.url_input]
        )
        
        self.start_btn.click(
            fn=self._on_start,
            inputs=[self.url_input, self.output_language, self.backend_mode],
            outputs=[self.progress_bar, self.status_text, self.summary_output]
        )
        
        self.qa_btn.click(
            fn=self._on_qa,
            inputs=[self.qa_input, self.chatbot],
            outputs=[self.chatbot, self.qa_input]
        )
        
        self.qa_input.submit(
            fn=self._on_qa,
            inputs=[self.qa_input, self.chatbot],
            outputs=[self.chatbot, self.qa_input]
        )
    
    def _on_file_upload(self, file_path):
        if file_path:
            return file_path
        return ""
    
    def _on_start(self, url, language, mode):
        if not url or not url.strip():
            return 0, "请输入URL或上传文件", "*请输入URL或上传文件*"
        
        lang_map = {
            "中文": Language.CHINESE,
            "English": Language.ENGLISH,
            "Deutsch": Language.GERMAN
        }
        output_lang = lang_map.get(language, Language.CHINESE)
        
        task_id = self.scheduler.create_task(url.strip())
        self.current_task_id = task_id
        
        try:
            loop = asyncio.get_event_loop()
            task = loop.run_until_complete(
                self.scheduler.process(task_id, url.strip(), output_lang)
            )
            
            if task.status == ProcessingStatus.COMPLETED:
                return (
                    100,
                    f"处理完成 - 耗时 {task.summary.processing_time:.1f}s",
                    task.summary.full_summary
                )
            else:
                return (
                    0,
                    f"处理失败: {task.error}",
                    f"*处理失败: {task.error}*"
                )
                
        except Exception as e:
            return 0, f"错误: {str(e)}", f"*错误: {str(e)}*"
    
    def _on_qa(self, question, chat_history):
        if not question or not question.strip():
            return chat_history, ""
        
        if not self.current_task_id:
            chat_history.append((question, "请先处理视频"))
            return chat_history, ""
        
        try:
            loop = asyncio.get_event_loop()
            answer = loop.run_until_complete(
                self.scheduler.qa(self.current_task_id, question.strip())
            )
            
            chat_history.append((question, answer))
            return chat_history, ""
            
        except Exception as e:
            chat_history.append((question, f"错误: {str(e)}"))
            return chat_history, ""


def create_app() -> gr.Blocks:
    ui = VideoSumUI()
    return ui.create_ui()
