"""VideoSum Flet UI"""

import flet as ft
import asyncio
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
        
        # UI组件引用
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
        """配置页面"""
        self.page.title = "VideoSum - 视频总结工具"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.window.width = 1200
        self.page.window.height = 800
        self.page.padding = 20
    
    def build(self) -> ft.Control:
        """构建UI"""
        
        # 标题
        header = ft.Container(
            content=ft.Column([
                ft.Text("🎬 VideoSum", size=32, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                ft.Text("本地智能视频总结与课件生成工具", size=14, color=ft.Colors.GREY_600, text_align=ft.TextAlign.CENTER),
            ]),
            padding=ft.padding.only(bottom=20),
        )
        
        # 左侧输入面板
        left_panel = self._build_input_panel()
        
        # 右侧输出面板
        right_panel = self._build_output_panel()
        
        # 主布局
        main_content = ft.Row(
            [
                ft.Container(left_panel, expand=1),
                ft.Container(right_panel, expand=2),
            ],
            expand=True,
            spacing=20,
        )
        
        # 底部状态栏
        status_bar = self._build_status_bar()
        
        return ft.Column(
            [
                header,
                main_content,
                status_bar,
            ],
            expand=True,
        )
    
    def _build_input_panel(self) -> ft.Control:
        """构建输入面板"""
        
        self.url_input = ft.TextField(
            label="视频URL或本地文件路径",
            hint_text="输入B站、YouTube链接，或点击下方按钮选择文件",
            multiline=True,
            min_lines=2,
            max_lines=4,
            width=350,
        )
        
        self.file_picker = ft.FilePicker(on_result=self._on_file_picked)
        self.page.overlay.append(self.file_picker)
        
        self.language_dropdown = ft.Dropdown(
            label="输出语言",
            options=[
                ft.dropdown.Option("中文"),
                ft.dropdown.Option("English"),
                ft.dropdown.Option("Deutsch"),
            ],
            value="中文",
            width=350,
        )
        
        self.start_button = ft.ElevatedButton(
            text="🚀 开始总结",
            on_click=self._on_start_click,
            width=350,
            height=50,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.BLUE_600,
                color=ft.Colors.WHITE,
            ),
        )
        
        self.progress_bar = ft.ProgressBar(
            width=350,
            value=0,
            visible=False,
        )
        
        self.status_text = ft.Text(
            "就绪",
            size=12,
            color=ft.Colors.GREY_600,
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Text("📥 输入", size=16, weight=ft.FontWeight.BOLD),
                self.url_input,
                ft.ElevatedButton(
                    "📁 选择本地文件",
                    on_click=lambda _: self.file_picker.pick_files(
                        dialog_title="选择视频或音频文件",
                        allowed_extensions=["mp4", "mkv", "avi", "mov", "mp3", "wav", "m4a"],
                        allow_multiple=False,
                    ),
                    width=350,
                ),
                self.language_dropdown,
                self.start_button,
                self.progress_bar,
                self.status_text,
            ], spacing=15),
            padding=20,
            border_radius=10,
            bgcolor=ft.Colors.GREY_50,
        )
    
    def _build_output_panel(self) -> ft.Control:
        """构建输出面板"""
        
        self.summary_output = ft.Markdown(
            "*暂无总结，请先处理视频*",
            selectable=True,
        )
        
        self.qa_input = ft.TextField(
            label="输入问题",
            hint_text="基于视频内容提问...",
            expand=True,
            on_submit=self._on_qa_submit,
        )
        
        self.chat_list = ft.ListView(
            spacing=10,
            height=300,
            auto_scroll=True,
        )
        
        # 标签页
        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(
                    content=ft.Container(
                        content=ft.Column([
                            self.summary_output,
                            ft.Row([
                                ft.ElevatedButton("📋 复制", on_click=self._on_copy),
                                ft.ElevatedButton("💾 导出", on_click=self._on_export),
                            ]),
                        ]),
                        padding=10,
                    ),
                    tab_content=ft.Text("📝 总结结果"),
                ),
                ft.Tab(
                    content=ft.Container(
                        content=ft.Column([
                            self.chat_list,
                            ft.Row([
                                self.qa_input,
                                ft.IconButton(
                                    icon=ft.Icons.SEND,
                                    on_click=self._on_qa_submit,
                                    icon_size=30,
                                ),
                            ]),
                        ]),
                        padding=10,
                    ),
                    tab_content=ft.Text("💬 问答助手"),
                ),
                ft.Tab(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text("📚 课件生成功能开发中...", color=ft.Colors.GREY_500),
                        ]),
                        padding=10,
                    ),
                    tab_content=ft.Text("📚 课件预览"),
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
    
    def _build_status_bar(self) -> ft.Control:
        """构建状态栏"""
        return ft.Container(
            content=ft.Row([
                ft.Text("ASR: 本地Whisper | LLM: DeepSeek | 语言: 中文", size=11, color=ft.Colors.GREY_600),
                ft.Text("预估费用: ¥0.00", size=11, color=ft.Colors.GREY_600),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=ft.padding.only(top=10),
        )
    
    def _on_file_picked(self, e):
        """文件选择回调"""
        if e.files:
            self.url_input.value = e.files[0].path
            self.page.update()
    
    def _on_start_click(self, e):
        """开始处理"""
        url = self.url_input.value.strip() if self.url_input.value else ""
        
        if not url:
            self.status_text.value = "❌ 请输入URL或选择文件"
            self.page.update()
            return
        
        # 显示进度
        self.progress_bar.visible = True
        self.progress_bar.value = 0
        self.status_text.value = "⏳ 处理中..."
        self.start_button.disabled = True
        self.page.update()
        
        # 映射语言
        lang_map = {
            "中文": Language.CHINESE,
            "English": Language.ENGLISH,
            "Deutsch": Language.GERMAN
        }
        output_lang = lang_map.get(self.language_dropdown.value, Language.CHINESE)
        
        # 创建任务
        task_id = self.scheduler.create_task(url)
        self.current_task_id = task_id
        
        # 异步处理
        def process_task():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                task = loop.run_until_complete(
                    self.scheduler.process(task_id, url, output_lang)
                )
                
                # 更新UI
                self.page.run_task(self._update_ui_after_process, task)
                
            except Exception as ex:
                self.page.run_task(self._handle_error, str(ex))
        
        import threading
        thread = threading.Thread(target=process_task, daemon=True)
        thread.start()
    
    async def _update_ui_after_process(self, task):
        """处理完成后更新UI"""
        self.progress_bar.value = 1.0
        self.start_button.disabled = False
        
        if task.status == ProcessingStatus.COMPLETED:
            self.status_text.value = f"✅ 处理完成 - 耗时 {task.summary.processing_time:.1f}s"
            self.summary_output.value = task.summary.full_summary
        else:
            self.status_text.value = f"❌ 处理失败: {task.error}"
            self.summary_output.value = f"*处理失败: {task.error}*"
        
        self.page.update()
    
    async def _handle_error(self, error_msg: str):
        """处理错误"""
        self.progress_bar.visible = False
        self.start_button.disabled = False
        self.status_text.value = f"❌ 错误: {error_msg}"
        self.page.update()
    
    def _on_qa_submit(self, e):
        """问答提交"""
        question = self.qa_input.value.strip() if self.qa_input.value else ""
        
        if not question:
            return
        
        if not self.current_task_id:
            self._add_chat_message("请先处理视频", is_user=False)
            return
        
        # 添加用户消息
        self._add_chat_message(question, is_user=True)
        self.qa_input.value = ""
        self.page.update()
        
        # 异步获取回答
        def get_answer():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                answer = loop.run_until_complete(
                    self.scheduler.qa(self.current_task_id, question)
                )
                
                self.page.run_task(self._add_chat_message, answer, False)
                
            except Exception as ex:
                self.page.run_task(self._add_chat_message, f"错误: {str(ex)}", False)
        
        import threading
        thread = threading.Thread(target=get_answer, daemon=True)
        thread.start()
    
    def _add_chat_message(self, message: str, is_user: bool = True):
        """添加聊天消息"""
        avatar = "👤" if is_user else "🤖"
        bg_color = ft.Colors.BLUE_100 if is_user else ft.Colors.GREY_100
        
        chat_bubble = ft.Container(
            content=ft.Row([
                ft.Text(avatar, size=20),
                ft.Container(
                    content=ft.Text(message, size=13, selectable=True),
                    padding=10,
                    border_radius=10,
                    bgcolor=bg_color,
                    expand=True,
                ),
            ]),
            alignment=ft.alignment.center_left if not is_user else ft.alignment.center_right,
        )
        
        self.chat_list.controls.append(chat_bubble)
        self.page.update()
    
    def _on_copy(self, e):
        """复制总结"""
        if self.summary_output.value:
            self.page.set_clipboard(self.summary_output.value)
            self.status_text.value = "📋 已复制到剪贴板"
            self.page.update()
    
    def _on_export(self, e):
        """导出总结"""
        self.status_text.value = "💾 导出功能开发中..."
        self.page.update()
