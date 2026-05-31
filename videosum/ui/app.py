"""VideoSum Gradio UI - 左侧导航栏版本"""

import gradio as gr
from typing import Optional
import logging

from videosum.config_manager import ConfigManager
from videosum.scheduler import Scheduler
from videosum.i18n import I18nManager

logger = logging.getLogger(__name__)


class VideoSumUI:
    """VideoSum Gradio界面"""
    
    def __init__(self):
        self.config = ConfigManager()
        self.scheduler = Scheduler(self.config)
        self.i18n = I18nManager(self.config.get("app.language", "zh"))
        self.current_task_id: Optional[str] = None
        
        # 页面组件引用
        self.pages = {}
    
    def create_ui(self) -> gr.Blocks:
        """创建Gradio界面"""
        
        with gr.Blocks(title="VideoSum") as app:
            gr.Markdown("# VideoSum - 本地智能视频总结工具")
            
            with gr.Row():
                # 左侧导航栏
                with gr.Column(scale=1, min_width=180):
                    self._create_sidebar()
                
                # 主内容区
                with gr.Column(scale=4):
                    self._create_main_content()
            
            self._setup_events()
        
        return app
    
    def _create_sidebar(self):
        """创建左侧导航栏"""
        gr.Markdown("### 导航")
        
        self.nav_buttons = []
        nav_items = [
            ("视频总结", "summary"),
            ("模型配置", "config"),
            ("日志", "logs"),
            ("任务历史", "history"),
            ("视频库", "library"),
            ("插件管理", "plugins"),
            ("成本统计", "stats"),
            ("导出设置", "export"),
            ("主题设置", "theme"),
            ("高级设置", "advanced"),
            ("使用帮助", "help"),
            ("关于", "about"),
        ]
        
        for label, key in nav_items:
            btn = gr.Button(label, size="sm", elem_id=f"nav_{key}")
            self.nav_buttons.append((key, btn))
    
    def _create_main_content(self):
        """创建主内容区"""
        # 使用gr.Tabs实现页面切换
        with gr.Tabs() as self.main_tabs:
            # 视频总结页
            with gr.Tab("视频总结", id="tab_summary"):
                self._create_summary_page()
            
            # 模型配置页
            with gr.Tab("模型配置", id="tab_config"):
                self._create_config_page()
            
            # 日志页
            with gr.Tab("日志", id="tab_logs"):
                self._create_logs_page()
            
            # 任务历史页
            with gr.Tab("任务历史", id="tab_history"):
                self._create_history_page()
            
            # 视频库页
            with gr.Tab("视频库", id="tab_library"):
                self._create_library_page()
            
            # 插件管理页
            with gr.Tab("插件管理", id="tab_plugins"):
                self._create_plugins_page()
            
            # 成本统计页
            with gr.Tab("成本统计", id="tab_stats"):
                self._create_stats_page()
            
            # 导出设置页
            with gr.Tab("导出设置", id="tab_export"):
                self._create_export_page()
            
            # 主题设置页
            with gr.Tab("主题设置", id="tab_theme"):
                self._create_theme_page()
            
            # 高级设置页
            with gr.Tab("高级设置", id="tab_advanced"):
                self._create_advanced_page()
            
            # 使用帮助页
            with gr.Tab("使用帮助", id="tab_help"):
                self._create_help_page()
            
            # 关于页
            with gr.Tab("关于", id="tab_about"):
                self._create_about_page()
    
    def _create_summary_page(self):
        """视频总结页"""
        with gr.Row():
            # 左侧：输入区
            with gr.Column(scale=1):
                gr.Markdown("### 输入")
                
                self.url_input = gr.Textbox(
                    label="视频URL或本地文件路径",
                    placeholder="输入B站、YouTube链接，或本地文件路径...",
                    lines=3
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
                
                self.start_btn = gr.Button("开始总结", variant="primary", size="lg")
                
                self.progress_bar = gr.Slider(
                    label="进度", minimum=0, maximum=100, value=0, interactive=False
                )
                
                self.status_text = gr.Textbox(label="状态", value="就绪", interactive=False)
            
            # 右侧：输出区
            with gr.Column(scale=2):
                with gr.Tabs():
                    with gr.Tab("总结结果"):
                        self.summary_output = gr.Markdown(value="*暂无总结*")
                        with gr.Row():
                            gr.Button("复制")
                            gr.Button("导出")
                    
                    with gr.Tab("问答助手"):
                        self.chatbot = gr.Chatbot(label="问答对话", height=350)
                        with gr.Row():
                            self.qa_input = gr.Textbox(
                                label="输入问题", placeholder="基于视频内容提问...", scale=4
                            )
                            self.qa_btn = gr.Button("发送", scale=1)
                    
                    with gr.Tab("课件预览"):
                        gr.Markdown("*课件生成功能开发中...*")
    
    def _create_config_page(self):
        """模型配置页"""
        gr.Markdown("### 模型配置")
        
        with gr.Tabs():
            # ASR配置
            with gr.Tab("ASR语音识别"):
                with gr.Row():
                    with gr.Column():
                        self.asr_backend = gr.Dropdown(
                            label="ASR后端",
                            choices=["local", "openai", "aliyun", "google"],
                            value="local"
                        )
                        self.asr_model_size = gr.Dropdown(
                            label="模型大小",
                            choices=["tiny", "base", "small", "medium", "large", "large-v3"],
                            value="large-v3"
                        )
                        self.asr_device = gr.Dropdown(
                            label="设备",
                            choices=["auto", "cuda", "cpu"],
                            value="auto"
                        )
                    with gr.Column():
                        self.asr_api_key = gr.Textbox(label="API密钥", type="password")
                        self.asr_test_btn = gr.Button("测试连接")
                        self.asr_test_result = gr.Textbox(label="测试结果", interactive=False)
            
            # LLM配置
            with gr.Tab("LLM大语言模型"):
                with gr.Row():
                    with gr.Column():
                        self.llm_backend = gr.Dropdown(
                            label="LLM供应商",
                            choices=["deepseek", "openai", "qwen", "kimi", "glm", "ollama"],
                            value="deepseek"
                        )
                        self.llm_model = gr.Textbox(label="模型名称", value="deepseek-chat")
                        self.llm_temperature = gr.Slider(
                            label="温度", minimum=0, maximum=1, value=0.3, step=0.1
                        )
                    with gr.Column():
                        self.llm_api_key = gr.Textbox(label="API密钥", type="password")
                        self.llm_test_btn = gr.Button("测试连接")
                        self.llm_test_result = gr.Textbox(label="测试结果", interactive=False)
            
            # 保存配置
            with gr.Tab("保存"):
                self.save_config_btn = gr.Button("保存配置", variant="primary")
                self.config_save_result = gr.Textbox(label="保存结果", interactive=False)
    
    def _create_logs_page(self):
        """日志页"""
        gr.Markdown("### 应用日志")
        
        with gr.Row():
            self.log_level = gr.Dropdown(
                label="日志级别",
                choices=["ALL", "DEBUG", "INFO", "WARNING", "ERROR"],
                value="ALL"
            )
            gr.Button("刷新")
            gr.Button("清空")
            gr.Button("导出")
        
        self.log_display = gr.Textbox(
            label="日志内容",
            lines=20,
            interactive=False
        )
    
    def _create_history_page(self):
        """任务历史页"""
        gr.Markdown("### 任务历史")
        
        with gr.Row():
            gr.Button("刷新")
            gr.Button("清空历史")
        
        self.history_table = gr.Dataframe(
            headers=["任务ID", "标题", "状态", "创建时间", "操作"],
            datatype=["str", "str", "str", "str", "str"],
            row_count=10
        )
    
    def _create_library_page(self):
        """视频库页"""
        gr.Markdown("### 视频库")
        
        with gr.Row():
            self.library_search = gr.Textbox(
                label="搜索", placeholder="搜索视频标题..."
            )
            gr.Button("搜索")
            gr.Button("刷新")
        
        self.library_table = gr.Dataframe(
            headers=["标题", "时长", "语言", "处理时间", "标签"],
            datatype=["str", "str", "str", "str", "str"],
            row_count=10
        )
    
    def _create_plugins_page(self):
        """插件管理页"""
        gr.Markdown("### 插件管理")
        
        with gr.Row():
            gr.Button("安装插件")
            gr.Button("刷新")
        
        self.plugins_table = gr.Dataframe(
            headers=["插件名称", "版本", "状态", "描述", "操作"],
            datatype=["str", "str", "str", "str", "str"],
            row_count=5
        )
        
        gr.Markdown("### 插件商店")
        gr.Markdown("*插件商店功能开发中...*")
    
    def _create_stats_page(self):
        """成本统计页"""
        gr.Markdown("### 成本统计")
        
        with gr.Row():
            with gr.Column():
                gr.Markdown("#### ASR费用")
                self.asr_cost_display = gr.Markdown("**¥0.00**")
            with gr.Column():
                gr.Markdown("#### LLM费用")
                self.llm_cost_display = gr.Markdown("**¥0.00**")
            with gr.Column():
                gr.Markdown("#### 总费用")
                self.total_cost_display = gr.Markdown("**¥0.00**")
        
        gr.Markdown("#### 费用趋势")
        gr.Markdown("*图表功能开发中...*")
    
    def _create_export_page(self):
        """导出设置页"""
        gr.Markdown("### 导出设置")
        
        with gr.Row():
            with gr.Column():
                self.export_format = gr.Radio(
                    label="导出格式",
                    choices=["Markdown", "HTML", "PDF"],
                    value="Markdown"
                )
                self.export_dir = gr.Textbox(
                    label="输出目录",
                    value="~/Videos/SummaryOutput"
                )
            with gr.Column():
                self.export_naming = gr.Textbox(
                    label="文件命名规则",
                    value="{title}_{date}",
                    placeholder="{title}_{date}"
                )
                gr.Button("保存设置", variant="primary")
    
    def _create_theme_page(self):
        """主题设置页"""
        gr.Markdown("### 主题设置")
        
        with gr.Row():
            with gr.Column():
                self.theme_mode = gr.Radio(
                    label="主题模式",
                    choices=["亮色", "暗色", "跟随系统"],
                    value="亮色"
                )
                self.font_size = gr.Slider(
                    label="字体大小",
                    minimum=12,
                    maximum=20,
                    value=14,
                    step=1
                )
            with gr.Column():
                self.ui_language = gr.Radio(
                    label="界面语言",
                    choices=["中文", "English", "Deutsch"],
                    value="中文"
                )
                gr.Button("应用设置", variant="primary")
    
    def _create_advanced_page(self):
        """高级设置页"""
        gr.Markdown("### 高级设置")
        
        with gr.Row():
            with gr.Column():
                self.temp_dir = gr.Textbox(
                    label="临时目录",
                    value="~/tmp/videosummary"
                )
                self.log_level_config = gr.Dropdown(
                    label="日志级别",
                    choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                    value="INFO"
                )
            with gr.Column():
                self.keep_temp_files = gr.Checkbox(label="保留临时文件", value=False)
                self.auto_save = gr.Checkbox(label="自动保存配置", value=True)
        
        with gr.Row():
            gr.Button("清理缓存", variant="secondary")
            gr.Button("保存设置", variant="primary")
    
    def _create_help_page(self):
        """使用帮助页"""
        gr.Markdown("""
        ### 使用帮助
        
        #### 快速入门
        1. 在"视频总结"页面输入视频URL或上传本地文件
        2. 选择输出语言
        3. 点击"开始总结"
        4. 等待处理完成，查看结果
        
        #### 常见问题
        
        **Q: 如何使用本地文件？**
        A: 直接在输入框输入文件路径，或点击"上传文件"按钮选择文件。
        
        **Q: 如何配置API密钥？**
        A: 在"模型配置"页面填写对应供应商的API密钥。
        
        **Q: 处理失败怎么办？**
        A: 检查"日志"页面查看错误信息，或在"模型配置"页面测试连接。
        
        #### 快捷键
        - `Enter`: 发送问题（问答模式）
        - `Ctrl+C`: 复制选中文本
        """)
    
    def _create_about_page(self):
        """关于页"""
        gr.Markdown("""
        ### 关于 VideoSum
        
        **版本**: v0.1.0
        
        **项目地址**: https://github.com/qquieen/videosum
        
        **功能特点**:
        - 支持B站、YouTube等视频链接
        - 支持本地视频/音频文件
        - 多语言支持（中文/英文/德文）
        - 本地/云端后端无缝切换
        - 隐私友好，数据不上传
        
        **技术栈**:
        - Python 3.10+
        - Gradio 6.x
        - faster-whisper (ASR)
        - OpenAI-compatible API (LLM)
        
        **许可证**: MIT License
        """)
    
    def _setup_events(self):
        """设置事件处理"""
        # 开始按钮
        self.start_btn.click(
            fn=self._on_start,
            inputs=[self.url_input, self.output_language],
            outputs=[self.progress_bar, self.status_text, self.summary_output]
        )
        
        # 问答按钮
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
    
    def _on_start(self, url, language):
        """开始处理"""
        if not url or not url.strip():
            return 0, "请输入URL或文件路径", "*请输入URL或文件路径*"
        
        from videosum.models import Language
        lang_map = {"中文": Language.CHINESE, "English": Language.ENGLISH, "Deutsch": Language.GERMAN}
        output_lang = lang_map.get(language, Language.CHINESE)
        
        task_id = self.scheduler.create_task(url.strip())
        self.current_task_id = task_id
        
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            task = loop.run_until_complete(
                self.scheduler.process(task_id, url.strip(), output_lang)
            )
            
            if task.status.value == "completed":
                return 100, f"完成 - {task.summary.processing_time:.1f}s", task.summary.full_summary
            else:
                return 0, f"失败: {task.error}", f"*失败: {task.error}*"
        except Exception as e:
            return 0, f"错误: {str(e)}", f"*错误: {str(e)}*"
    
    def _on_qa(self, question, chat_history):
        """问答处理"""
        if not question or not question.strip():
            return chat_history, ""
        
        if not self.current_task_id:
            chat_history.append((question, "请先处理视频"))
            return chat_history, ""
        
        try:
            import asyncio
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
    """创建应用实例"""
    ui = VideoSumUI()
    return ui.create_ui()
