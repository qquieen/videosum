"""图文笔记生成模块"""

import logging
from typing import List, Dict, Optional
from pathlib import Path
import base64

logger = logging.getLogger(__name__)


class NotesGenerator:
    """图文笔记生成器"""
    
    def __init__(self):
        pass
    
    def generate(
        self,
        summary: str,
        frames: List[Dict],
        include_images: bool = True
    ) -> str:
        """
        生成图文笔记
        
        Args:
            summary: 文本总结
            frames: 关键帧列表 [{"path": str, "timestamp": float, "description": str}]
            include_images: 是否包含图片（False则只包含链接）
        
        Returns:
            Markdown格式的图文笔记
        """
        notes = []
        
        # 标题
        notes.append("# 📚 视频笔记\n")
        
        # 目录
        notes.append("## 📋 目录\n")
        notes.append("- [视频总结](#视频总结)")
        notes.append("- [关键帧笔记](#关键帧笔记)")
        notes.append("")
        
        # 视频总结
        notes.append("## 📝 视频总结\n")
        notes.append(summary)
        notes.append("")
        
        # 关键帧笔记
        if frames:
            notes.append("## 🖼️ 关键帧笔记\n")
            
            for i, frame in enumerate(frames):
                timestamp = frame.get("timestamp", 0)
                description = frame.get("description", "暂无描述")
                frame_path = frame.get("path", "")
                
                # 时间戳格式化
                minutes = int(timestamp // 60)
                seconds = int(timestamp % 60)
                time_str = f"{minutes:02d}:{seconds:02d}"
                
                notes.append(f"### 帧 {i+1} - [{time_str}]\n")
                
                # 图片
                if include_images and frame_path:
                    if Path(frame_path).exists():
                        # 嵌入base64图片
                        notes.append(self._embed_image(frame_path))
                    else:
                        notes.append(f"![帧 {i+1}]({frame_path})")
                else:
                    notes.append(f"📁 图片路径: `{frame_path}`")
                
                notes.append("")
                
                # 描述
                if description:
                    notes.append(f"**描述**: {description}")
                    notes.append("")
        
        # 页脚
        notes.append("---")
        notes.append("*由 VideoSum Vision Plugin 生成*")
        
        return "\n".join(notes)
    
    def _embed_image(self, image_path: str) -> str:
        """将图片嵌入Markdown（base64）"""
        try:
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            
            # 获取图片类型
            suffix = Path(image_path).suffix.lower()
            mime_type = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".webp": "image/webp"
            }.get(suffix, "image/jpeg")
            
            return f"![帧]({mime_type};base64,{image_data})"
            
        except Exception as e:
            logger.warning(f"嵌入图片失败: {e}")
            return f"![帧]({image_path})"
    
    def generate_html(
        self,
        summary: str,
        frames: List[Dict]
    ) -> str:
        """
        生成HTML格式的图文笔记
        
        Args:
            summary: 文本总结
            frames: 关键帧列表
        
        Returns:
            HTML格式的图文笔记
        """
        html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>视频笔记 - VideoSum</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
        .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }
        h2 { color: #555; margin-top: 30px; }
        .frame { background: #f9f9f9; padding: 15px; border-radius: 8px; margin: 15px 0; }
        .frame img { max-width: 100%; border-radius: 5px; }
        .timestamp { color: #007bff; font-weight: bold; }
        .description { color: #666; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>📚 视频笔记</h1>
        
        <h2>📝 视频总结</h2>
        <div class="summary">"""
        
        # 简单的Markdown转HTML
        summary_html = summary.replace("\n", "<br>")
        html += summary_html
        
        html += """
        </div>
        
        <h2>🖼️ 关键帧笔记</h2>
        """
        
        for i, frame in enumerate(frames):
            timestamp = frame.get("timestamp", 0)
            description = frame.get("description", "暂无描述")
            frame_path = frame.get("path", "")
            
            minutes = int(timestamp // 60)
            seconds = int(timestamp % 60)
            time_str = f"{minutes:02d}:{seconds:02d}"
            
            html += f"""
        <div class="frame">
            <span class="timestamp">⏱️ [{time_str}]</span>
            <img src="{frame_path}" alt="帧 {i+1}">
            <p class="description">{description}</p>
        </div>
            """
        
        html += """
    </div>
</body>
</html>"""
        
        return html
