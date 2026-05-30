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
        help="Web服务器地址（默认: 127.0.0.1）"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Web服务器端口（默认: 8080）"
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="以Web模式运行"
    )
    
    args = parser.parse_args()
    
    # 配置日志
    setup_logging()
    
    if args.no_ui:
        # 命令行模式
        print("VideoSum 命令行模式")
        print("请使用 --help 查看帮助")
        return
    
    # Flet界面模式
    try:
        import flet as ft
        
        print("🚀 启动 VideoSum...")
        
        if args.web:
            # Web模式
            print(f"📍 访问地址: http://{args.host}:{args.port}")
            ft.app(
                target=main,
                view=ft.WEB_BROWSER,
                port=args.port,
                host=args.host,
            )
        else:
            # 桌面模式
            ft.app(target=main)
        
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("请运行: pip install flet")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)


def main(page: ft.Page):
    """Flet主函数"""
    from videosum.ui.app import VideoSumApp
    
    app = VideoSumApp(page)
    page.add(app.build())


if __name__ == "__main__":
    main()
