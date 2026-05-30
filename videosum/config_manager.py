from pathlib import Path
from typing import Any, Dict, Optional
import yaml
import logging

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_DIR = Path.home() / ".videosummary"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.yaml"

DEFAULT_CONFIG = {
    "app": {
        "output_dir": "~/Videos/SummaryOutput",
        "temp_dir": "~/tmp/videosummary",
        "keep_temp_files": False,
        "language": "zh",
    },
    "asr": {
        "backend": "local",
        "local": {
            "model_size": "large-v3",
            "device": "auto",
            "compute_type": "float16",
        },
        "openai": {"api_key": ""},
        "aliyun": {
            "access_key_id": "",
            "access_key_secret": "",
            "app_key": "",
            "region": "cn-shanghai",
        },
        "google": {"api_key": ""},
    },
    "llm": {
        "backend": "deepseek",
        "openai": {"api_key": "", "model": "gpt-4.1-mini"},
        "anthropic": {"api_key": "", "model": "claude-sonnet-4-20250514"},
        "google": {"api_key": "", "model": "gemini-2.5-flash"},
        "deepseek": {"api_key": "", "model": "deepseek-chat"},
        "qwen": {"api_key": "", "model": "qwen-plus"},
        "kimi": {"api_key": "", "model": "moonshot-v1-128k"},
        "glm": {"api_key": "", "model": "glm-4-plus"},
        "ollama": {"model": "qwen2.5:7b", "context_length": 8192},
        "temperature": 0.3,
        "max_tokens": 4000,
    },
    "visual": {
        "enabled": False,
        "backend": "local",
        "local": {
            "model": "llava:7b",
            "frame_interval": 10,
            "min_scene_change_threshold": 30,
        },
    },
    "rag": {
        "embedding_model": "BAAI/bge-m3",
        "chroma_persist_dir": "~/.videosummary/chroma_db",
    },
    "budget": {
        "currency": "CNY",
        "warn_threshold": 5.0,
    },
}


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir) if config_dir else DEFAULT_CONFIG_DIR
        self.config_file = self.config_dir / "config.yaml"
        self._config: Dict[str, Any] = {}
        self.load()
    
    def load(self) -> Dict[str, Any]:
        """加载配置文件"""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self._config = yaml.safe_load(f) or {}
                logger.info(f"配置已加载: {self.config_file}")
            except Exception as e:
                logger.warning(f"加载配置失败: {e}，使用默认配置")
                self._config = DEFAULT_CONFIG.copy()
        else:
            logger.info("配置文件不存在，使用默认配置")
            self._config = DEFAULT_CONFIG.copy()
            self.save()
        
        return self._config
    
    def save(self) -> None:
        """保存配置文件"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                yaml.dump(self._config, f, allow_unicode=True, default_flow_style=False)
            logger.info(f"配置已保存: {self.config_file}")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            raise
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项（支持点号分隔的路径）"""
        keys = key.split(".")
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            
            if value is None:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """设置配置项（支持点号分隔的路径）"""
        keys = key.split(".")
        config = self._config
        
        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def update(self, updates: Dict[str, Any]) -> None:
        """批量更新配置"""
        def deep_update(base: dict, updates: dict):
            for key, value in updates.items():
                if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                    deep_update(base[key], value)
                else:
                    base[key] = value
        
        deep_update(self._config, updates)
    
    def reset(self) -> None:
        """重置为默认配置"""
        self._config = DEFAULT_CONFIG.copy()
        self.save()
    
    @property
    def config(self) -> Dict[str, Any]:
        return self._config
    
    def get_asr_config(self) -> Dict[str, Any]:
        """获取ASR配置"""
        return self._config.get("asr", DEFAULT_CONFIG["asr"])
    
    def get_llm_config(self) -> Dict[str, Any]:
        """获取LLM配置"""
        return self._config.get("llm", DEFAULT_CONFIG["llm"])
    
    def get_app_config(self) -> Dict[str, Any]:
        """获取应用配置"""
        return self._config.get("app", DEFAULT_CONFIG["app"])
