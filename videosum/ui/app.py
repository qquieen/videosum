"""VideoSum Gradio UI"""

import gradio as gr
import logging
import asyncio
import time
from typing import Optional, Tuple

from videosum.config_manager import ConfigManager
from videosum.scheduler import Scheduler
from videosum.models import Language, ProcessingStatus

logger = logging.getLogger(__name__)

class VideoSumUI:
    """VideoSum Gradio应用"""
    
    def __init__(self):
        self.config = ConfigManager()
        self.scheduler = Scheduler(self.config)
        self.current_task_id: Optional[str] = None

    def _process_video(self, url: str, file_obj: Optional[str], language: str, progress=gr.Progress()):
        """处理视频的包装器"""
        input_source = url.strip() if url.strip() else file_obj
        if not input_source:
            return "❌ 请输入URL或选择文件", "", []

        lang_map = {"中文": Language.CHINESE, "English": Language.ENGLISH, "Deutsch": Language.GERMAN}
        output_lang = lang_map.get(language, Language.CHINESE)

        # 创建任务
        task_id = self.scheduler.create_task(input_source)
        self.current_task_id = task_id

        # 定义进度回调
        def update_progress(p, msg):
            progress(p, desc=msg)

        # 运行异步处理
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            task = loop.run_until_complete(
                self.scheduler.process(task_id, input_source, output_lang, progress_callback=update_progress)
            )
            
            if task.status == ProcessingStatus.COMPLETED:
                return (
                    f"✅ 处理完成！耗时: {task.summary.processing_time:.1f}s",
                    task.summary.full_summary,
                    task.summary.key_points
                )
            else:
                return f"❌ 处理失败: {task.error}", "", []
        except Exception as e:
            logger.error(f"UI 处理异常: {e}")
            return f"❌ 运行出错: {str(e)}", "", []

    def _chat(self, message, history):
        """问答交互"""
        if not self.current_task_id:
            return history + [[message, "请先处理视频后再提问。"]]
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            answer = loop.run_until_complete(
                self.scheduler.qa(self.current_task_id, message)
            )
            return history + [[message, answer]]
        except Exception as e:
            return history + [[message, f"❌ 问答出错: {str(e)}"]]

    def build(self):
        """构建 Gradio 界面"""
        with gr.Blocks(theme=gr.themes.Soft(), title="VideoSum - 智能视频总结", css=".gradio-container {max-width: 1200px !important;}") as demo:
            gr.Markdown("# 🎬 VideoSum")
            gr.Markdown("### 本地智能视频总结与课件生成工具")
            
            with gr.Row():
                # 左侧：配置与输入
                with gr.Column(scale=1):
                    with gr.Group():
                        gr.Markdown("#### 📥 输入源")
                        url_input = gr.Textbox(label="视频 URL", placeholder="支持 B站、YouTube 等")
                        file_input = gr.File(label="或上传本地文件", file_types=["video", "audio"])
                    
                    with gr.Group():
                        gr.Markdown("#### ⚙️ 配置")
                        lang_select = gr.Dropdown(choices=["中文", "English", "Deutsch"], value="中文", label="总结语言")
                        backend_info = gr.Markdown(f"*当前后端: {self.config.get('asr.backend', 'local')} / {self.config.get('llm.backend', 'deepseek')}*")
                    
                    btn_run = gr.Button("🚀 开始总结", variant="primary")
                    status_output = gr.Textbox(label="状态", interactive=False)

                # 右侧：输出结果
                with gr.Column(scale=2):
                    with gr.Tabs():
                        with gr.TabItem("📝 总结结果"):
                            summary_md = gr.Markdown("处理完成后此处将显示总结内容...")
                            with gr.Row():
                                btn_copy = gr.Button("📋 复制总结")
                                btn_export = gr.Button("💾 导出 Markdown")
                        
                        with gr.TabItem("💬 问答助手"):
                            chatbot = gr.Chatbot(label="与视频对话", height=500)
                            msg_input = gr.Textbox(label="提问", placeholder="视频讲了什么？具体在哪个时间点？")
                            btn_clear = gr.ClearButton([msg_input, chatbot])

                        with gr.TabItem("📚 关键要点"):
                            key_points = gr.JSON(label="核心知识点")

            # 绑定事件
            btn_run.click(
                fn=self._process_video,
                inputs=[url_input, file_input, lang_select],
                outputs=[status_output, summary_md, key_points]
            )
            
            msg_input.submit(self._chat, [msg_input, chatbot], [chatbot])
            msg_input.submit(lambda: "", None, [msg_input]) # 清空输入框

        return demo

def launch():
    ui = VideoSumUI()
    demo = ui.build()
    demo.launch(server_name="127.0.0.1", server_port=8080)

if __name__ == "__main__":
    launch()
