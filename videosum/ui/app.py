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
        
        with gr.Blocks(
            title="VideoSum",
            theme=gr.themes.Soft(),
            css="""
            .main-title {
                text-align: center;
                margin-bottom: 20px;
            }
            .start-btn {
                height: 50px !important;
                font-size: 18px !important;
            }
            """
        ) as app:
            # 标题
            gr.HTML("""
            <div class="main-title">
                <h1>🎬 VideoSum</h1>
                <p>本地智能视频总结与课件生成工具</p>
            </div>
            """)
            
            with gr.Row():
                # 左侧面板
                with gr.Column(scale=1):
                    self._create_input_panel()
                
                # 右侧面板
                with gr.Column(scale=2):
                    self._create_output_panel()
            
            # 底部状态栏
            self._create_status_bar()
        
        return app
    
    def _create_input_panel(self):
        """创建输入面板"""
        with gr.Group():
            gr.Markdown("### 📥 输入")
            
            # URL输入框
            self.url_input = gr.Textbox(
                label="视频URL或本地文件路径",
                placeholder="输入B站、YouTube链接，或拖拽文件到下方...",
                lines=2
            )
            
            # 文件上传（支持拖拽）
            self.file_input = gr.File(
                label="或拖拽文件到此处",
                file_types=["video", "audio"],
                type="filepath"
            )
            
            # 语言选择
            self.output_language = gr.Radio(
                label="输出语言",
                choices=["中文", "English", "Deutsch"],
                value="中文"
            )
            
            # 后端模式
            self.backend_mode = gr.Radio(
                label="后端模式",
                choices=["推荐", "纯本地", "纯云端"],
                value="推荐"
            )
            
            # 开始按钮
            self.start_btn = gr.Button(
                "🚀 开始总结",
                variant="primary",
                size="lg",
                elem_classes=["start-btn"]
            )
            
            # 进度显示
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
        """创建输出面板"""
        with gr.Tabs():
            # 总结结果标签页
            with gr.TabItem("📝 总结结果"):
                self.summary_output = gr.Markdown(
                    value="*暂无总结，请先处理视频*"
                )
                with gr.Row():
                    self.copy_btn = gr.Button("📋 复制")
                    self.export_btn = gr.Button("💾 导出")
            
            # 问答助手标签页
            with gr.TabItem("💬 问答助手"):
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
            
            # 课件预览标签页
            with gr.TabItem("📚 课件预览"):
                gr.Markdown("*课件生成功能开发中...*")
    
    def _create_status_bar(self):
        """创建状态栏"""
        with gr.Row():
            gr.Markdown("**当前配置**：ASR=本地Whisper | LLM=DeepSeek | 语言=中文")
            self.cost_display = gr.Markdown("**预估费用**：¥0.00")
    
    def _setup_events(self):
        """设置事件处理"""
        
        # 文件上传时自动填入路径
        self.file_input.change(
            fn=self._on_file_upload,
            inputs=[self.file_input],
            outputs=[self.url_input]
        )
        
        # 开始按钮点击
        self.start_btn.click(
            fn=self._on_start,
            inputs=[self.url_input, self.output_language, self.backend_mode],
            outputs=[
                self.progress_bar,
                self.status_text,
                self.summary_output
            ]
        )
        
        # 问答按钮点击
        self.qa_btn.click(
            fn=self._on_qa,
            inputs=[self.qa_input, self.chatbot],
            outputs=[self.chatbot, self.qa_input]
        )
        
        # 问答回车
        self.qa_input.submit(
            fn=self._on_qa,
            inputs=[self.qa_input, self.chatbot],
            outputs=[self.chatbot, self.qa_input]
        )
    
    def _on_file_upload(self, file_path):
        """文件上传回调"""
        if file_path:
            return file_path
        return ""
    
    def _on_start(self, url, language, mode):
        """开始处理"""
        if not url or not url.strip():
            return 0, "请输入URL或上传文件", "*请输入URL或上传文件*"
        
        # 映射语言
        lang_map = {
            "中文": Language.CHINESE,
            "English": Language.ENGLISH,
            "Deutsch": Language.GERMAN
        }
        output_lang = lang_map.get(language, Language.CHINESE)
        
        # 创建任务
        task_id = self.scheduler.create_task(url.strip())
        self.current_task_id = task_id
        
        # 运行处理
        try:
            loop = asyncio.get_event_loop()
            task = loop.run_until_complete(
                self.scheduler.process(
                    task_id,
                    url.strip(),
                    output_lang
                )
            )
            
            # 更新UI
            if task.status == ProcessingStatus.COMPLETED:
                return (
                    100,
                    f"✅ 处理完成 - 耗时 {task.summary.processing_time:.1f}s",
                    task.summary.full_summary
                )
            else:
                return (
                    0,
                    f"❌ 处理失败: {task.error}",
                    f"*处理失败: {task.error}*"
                )
                
        except Exception as e:
            return 0, f"❌ 错误: {str(e)}", f"*错误: {str(e)}*"
    
    def _on_qa(self, question, chat_history):
        """问答处理"""
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
    
    def launch(self, **kwargs):
        """启动应用"""
        app = self.create_ui()
        self._setup_events()
        app.launch(**kwargs)


def create_app() -> gr.Blocks:
    """创建应用实例"""
    ui = VideoSumUI()
    app = ui.create_ui()
    ui._setup_events()
    return app
