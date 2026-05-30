# 🎬 VideoSum

本地智能视频总结与课件生成工具

## ✨ 功能特点

- 📥 **多源输入**：支持B站、YouTube链接，或拖拽本地视频/音频文件
- 🎯 **精准转写**：使用Whisper模型进行语音识别，支持多语言自动检测
- 📝 **智能总结**：LLM生成带时间戳的结构化总结
- 💬 **问答交互**：基于视频内容的智能问答
- 🔒 **隐私友好**：所有处理在本地完成，数据不上传
- 💰 **成本透明**：云端处理前预估费用
- 🌍 **多语言**：支持中文/English/Deutsch

## 🚀 快速开始

### 方式一：开发者安装

```bash
# 克隆仓库
git clone https://github.com/qquieen/videosum.git
cd videosum

# 安装依赖
pip install -r requirements.txt

# 启动应用
python main.py
```

### 方式二：一键运行版（开发中）

下载对应平台的可执行文件，双击运行即可。

## 📋 系统要求

- Python 3.10+
- FFmpeg（用于音频处理）
- yt-dlp（用于视频下载）

### 安装FFmpeg

**Windows:**
```bash
# 使用winget
winget install ffmpeg

# 或下载: https://www.gyan.dev/ffmpeg/builds/
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt install ffmpeg
```

## 🔧 配置

首次运行会自动创建配置文件 `~/.videosummary/config.yaml`

### 配置LLM API

在配置文件中设置API密钥：

```yaml
llm:
  backend: "deepseek"  # 或 openai, qwen, kimi, glm
  deepseek:
    api_key: "your-api-key"
    model: "deepseek-chat"
```

### 支持的LLM供应商

| 供应商 | 注册地址 |
|--------|----------|
| DeepSeek | https://platform.deepseek.com |
| 通义千问 | https://dashscope.aliyun.com |
| Moonshot (Kimi) | https://platform.moonshot.cn |
| 智谱 (GLM) | https://open.bigmodel.cn |
| OpenAI | https://platform.openai.com |

## 📁 项目结构

```
VIDEOSUM/
├── videosum/
│   ├── models.py          # 数据模型
│   ├── config_manager.py  # 配置管理
│   ├── downloader.py      # 下载模块（支持URL和本地文件）
│   ├── scheduler.py       # 核心调度器
│   ├── asr/               # ASR引擎
│   ├── llm/               # LLM引擎
│   ├── i18n/              # 多语言
│   └── ui/                # Gradio界面
├── main.py                # 主入口
├── requirements.txt       # 依赖
└── 开发文档.md            # 设计文档
```

## 🛠️ 开发

```bash
# 安装开发依赖
pip install -r requirements.txt

# 运行测试
pytest tests/

# 启动开发服务器
python main.py --port 7860
```

## 📦 打包

### 一键运行版（PyInstaller）

```bash
# 安装PyInstaller
pip install pyinstaller

# 打包
pyinstaller --onefile --name VideoSum main.py
```

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

## 🙏 致谢

- [Whisper](https://github.com/openai/whisper) - 语音识别
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - 视频下载
- [Gradio](https://gradio.app) - Web界面
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) - 高效Whisper实现
