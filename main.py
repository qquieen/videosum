#!/usr/bin/env python3
"""
VideoSum - 本地智能视频总结与课件生成工具
"""

import sys
import argparse
import logging
from pathlib import Path

import gradio as gr


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
        default=7860,
        help="Web服务器端口（默认: 7860）"
    )
    parser.add_argument(
        "--share",
        action="store_true",
        help="创建公共链接"
    )
    
    args = parser.parse_args()
    
    # 配置日志
    setup_logging()
    
    if args.no_ui:
        # 命令行模式
        print("VideoSum 命令行模式")
        print("请使用 --help 查看帮助")
        return
    
    # Web界面模式
    try:
        from videosum.ui.app import create_app
        
        print("🚀 启动 VideoSum...")
        print(f"📍 访问地址: http://{args.host}:{args.port}")
        
        app = create_app()
        app.launch(
            server_name=args.host,
            server_port=args.port,
            share=args.share,
            inbrowser=True,
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
        )
        
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("请运行: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
