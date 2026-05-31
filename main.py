#!/usr/bin/env python3
"""
VideoSum - 本地智能视频总结与课件生成工具
"""

import sys
import argparse
import logging
from pathlib import Path

import flet as ft


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


def flet_main(page: ft.Page):
    """Flet主函数"""
    from videosum.ui.app import VideoSumApp
    
    app = VideoSumApp(page)
    page.add(app.build())


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description="VideoSum - 本地智能视频总结与课件生成工具"
    )
    parser.add_argument(
        "--no-ui",
        action="store_true",
        help="不启动界面（命令行模式）"
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
    parser.add_argument(
        "--web",
        action="store_true",
        help="以Web模式运行"
    )
    
    args = parser.parse_args()
    
    setup_logging()
    
    if args.no_ui:
        print("VideoSum 命令行模式")
        return
    
    print("🚀 启动 VideoSum...")
    
    if args.web:
        print(f"📍 访问地址: http://{args.host}:{args.port}")
        ft.app(
            target=flet_main,
            view=ft.AppView.WEB_BROWSER,
            port=args.port,
            host=args.host,
        )
    else:
        ft.app(target=flet_main)


if __name__ == "__main__":
    main()
