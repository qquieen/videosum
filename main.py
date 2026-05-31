#!/usr/bin/env python3
"""
VideoSum - 本地智能视频总结与课件生成工具
"""

import sys
import argparse
import logging
from pathlib import Path


def setup_logging():
    """配置日志"""
    log_dir = Path.home() / ".videosummary" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "app.log", encoding="utf-8"),
            logging.StreamHandler()
        ]
    )


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="VideoSum - 本地智能视频总结与课件生成工具"
    )
    parser.add_argument(
        "--no-ui",
        action="store_true",
        help="不启动Web界面（命令行模式）"
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="服务器地址（默认: 127.0.0.1）"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="服务器端口（默认: 8080）"
    )
    
    args = parser.parse_args()
    
    # 配置日志
    setup_logging()
    
    if args.no_ui:
        # 命令行模式
        print("VideoSum 命令行模式已就绪。")
        # TODO: 实现 CLI 处理逻辑
        return
    
    # 启动 Gradio 界面
    print("🚀 正在启动 VideoSum (Gradio 版)...")
    from videosum.ui.app import VideoSumUI
    
    ui = VideoSumUI()
    demo = ui.build()
    
    print(f"📍 访问地址: http://{args.host}:{args.port}")
    demo.launch(
        server_name=args.host,
        server_port=args.port,
        share=False,
        inbrowser=True
    )


if __name__ == "__main__":
    main()
