"""VideoSum Flet UI"""

import flet as ft
import asyncio
import threading
from typing import Optional
import logging

from videosum.config_manager import ConfigManager
from videosum.scheduler import Scheduler
from videosum.models import Language, ProcessingStatus
from videosum.i18n import I18nManager

logger = logging.getLogger(__name__)


class VideoSumApp:
    """VideoSum Flet应用"""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.config = ConfigManager()
        self.scheduler = Scheduler(self.config)
        self.i18n = I18nManager(self.config.get("app.language", "zh"))
        self.current_task_id: Optional[str] = None
        
        # UI组件
        self.url_input: Optional[ft.TextField] = None
        self.file_picker: Optional[ft.FilePicker] = None
        self.language_dropdown: Optional[ft.Dropdown] = None
        self.start_button: Optional[ft.ElevatedButton] = None
        self.progress_bar: Optional[ft.ProgressBar] = None
        self.status_text: Optional[ft.Text] = None
        self.summary_output: Optional[ft.Markdown] = None
        self.qa_input: Optional[ft.TextField] = None
        self.chat_list: Optional[ft.ListView] = None
        
        self._setup_page()
    
    def _setup_page(self):
        self.page.title = "VideoSum"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.window.width = 1200
        self.page.window.height = 800
        self.page.padding = 20
    
    def build(self) -> ft.Control:
        header = ft.Container(
            content=ft.Column([
                ft.Text("🎬 VideoSum", size=28, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                ft.Text("本地智能视频总结工具", size=12, color=ft.Colors.GREY_600, text_align=ft.TextAlign.CENTER),
            ]),
            padding=ft.padding.all(0),
            margin=ft.margin.only(bottom=15),
        )
        
        left_panel = self._build_input_panel()
        right_panel = self._build_output_panel()
        
        main_content = ft.Row(
            [left_panel, right_panel],
            expand=True,
            spacing=20,
        )
        
        status_bar = ft.Container(
            content=ft.Row([
                ft.Text("ASR: 本地Whisper | LLM: DeepSeek", size=10, color=ft.Colors.GREY_600),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=ft.padding.all(0),
            margin=ft.margin.only(top=10),
        )
        
        return ft.Column([header, main_content, status_bar], expand=True)
    
    def _build_input_panel(self) -> ft.Control:
        self.url_input = ft.TextField(
            label="视频URL或本地文件路径",
            hint_text="输入链接或点击下方选择文件",
            multiline=True,
            min_lines=2,
            max_lines=3,
            width=320,
        )
        
        self.file_picker = ft.FilePicker(on_result=self._on_file_picked)
        self.page.overlay.append(self.file_picker)
        
        self.language_dropdown = ft.Dropdown(
            label="输出语言",
            options=[ft.dropdown.Option("中文"), ft.dropdown.Option("English"), ft.dropdown.Option("Deutsch")],
            value="中文",
            width=320,
        )
        
        self.start_button = ft.ElevatedButton(
            text="🚀 开始总结",
            on_click=self._on_start_click,
            width=320,
            height=45,
            style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE),
        )
        
        self.progress_bar = ft.ProgressBar(width=320, value=0, visible=False)
        self.status_text = ft.Text("就绪", size=11, color=ft.Colors.GREY_600)
        
        return ft.Container(
            content=ft.Column([
                ft.Text("📥 输入", size=14, weight=ft.FontWeight.BOLD),
                self.url_input,
                ft.ElevatedButton(
                    "📁 选择本地文件",
                    on_click=lambda _: self.file_picker.pick_files(
                        allowed_extensions=["mp4", "mkv", "avi", "mov", "mp3", "wav", "m4a"],
                    ),
                    width=320,
                ),
                self.language_dropdown,
                self.start_button,
                self.progress_bar,
                self.status_text,
            ], spacing=12),
            padding=15,
            border_radius=10,
            bgcolor=ft.Colors.GREY_50,
        )
    
    def _build_output_panel(self) -> ft.Control:
        self.summary_output = ft.Markdown("*暂无总结*", selectable=True)
        
        self.qa_input = ft.TextField(
            label="输入问题",
            hint_text="基于视频内容提问...",
            expand=True,
            on_submit=self._on_qa_submit,
        )
        
        self.chat_list = ft.ListView(spacing=8, height=250, auto_scroll=True)
        
        tabs = ft.Tabs(
            selected_index=0,
            tabs=[
                ft.Tab(
                    content=ft.Container(
                        content=ft.Column([self.summary_output]),
                        padding=10,
                    ),
                    tab_content=ft.Text("📝 总结"),
                ),
                ft.Tab(
                    content=ft.Container(
                        content=ft.Column([
                            self.chat_list,
                            ft.Row([
                                self.qa_input,
                                ft.IconButton(icon=ft.Icons.SEND, on_click=self._on_qa_submit),
                            ]),
                        ]),
                        padding=10,
                    ),
                    tab_content=ft.Text("💬 问答"),
                ),
            ],
            expand=True,
        )
        
        return ft.Container(
            content=tabs,
            border_radius=10,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.GREY_300),
        )
    
    def _on_file_picked(self, e):
        if e.files:
            self.url_input.value = e.files[0].path
            self.page.update()
    
    def _on_start_click(self, e):
        url = self.url_input.value.strip() if self.url_input.value else ""
        if not url:
            self.status_text.value = "❌ 请输入URL或选择文件"
            self.page.update()
            return
        
        self.progress_bar.visible = True
        self.progress_bar.value = 0
        self.status_text.value = "⏳ 处理中..."
        self.start_button.disabled = True
        self.page.update()
        
        lang_map = {"中文": Language.CHINESE, "English": Language.ENGLISH, "Deutsch": Language.GERMAN}
        output_lang = lang_map.get(self.language_dropdown.value, Language.CHINESE)
        
        task_id = self.scheduler.create_task(url)
        self.current_task_id = task_id
        
        def process_task():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                task = loop.run_until_complete(self.scheduler.process(task_id, url, output_lang))
                self.page.run_task(self._on_process_complete, task)
            except Exception as ex:
                self.page.run_task(self._on_process_error, str(ex))
        
        threading.Thread(target=process_task, daemon=True).start()
    
    async def _on_process_complete(self, task):
        self.progress_bar.value = 1.0
        self.start_button.disabled = False
        if task.status == ProcessingStatus.COMPLETED:
            self.status_text.value = f"✅ 完成 - {task.summary.processing_time:.1f}s"
            self.summary_output.value = task.summary.full_summary
        else:
            self.status_text.value = f"❌ 失败: {task.error}"
        self.page.update()
    
    async def _on_process_error(self, msg):
        self.progress_bar.visible = False
        self.start_button.disabled = False
        self.status_text.value = f"❌ {msg}"
        self.page.update()
    
    def _on_qa_submit(self, e):
        question = self.qa_input.value.strip() if self.qa_input.value else ""
        if not question or not self.current_task_id:
            return
        
        self._add_chat(question, True)
        self.qa_input.value = ""
        self.page.update()
        
        def get_answer():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                answer = loop.run_until_complete(self.scheduler.qa(self.current_task_id, question))
                self.page.run_task(self._add_chat, answer, False)
            except Exception as ex:
                self.page.run_task(self._add_chat, f"错误: {ex}", False)
        
        threading.Thread(target=get_answer, daemon=True).start()
    
    def _add_chat(self, message: str, is_user: bool):
        bg = ft.Colors.BLUE_100 if is_user else ft.Colors.GREY_100
        bubble = ft.Container(
            content=ft.Text(message, size=12, selectable=True),
            padding=8,
            border_radius=8,
            bgcolor=bg,
        )
        self.chat_list.controls.append(bubble)
        self.page.update()
