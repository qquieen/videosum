from pathlib import Path
from typing import Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

I18N_DIR = Path(__file__).parent
SUPPORTED_LANGUAGES = ["zh", "en", "de"]
DEFAULT_LANGUAGE = "zh"


class I18nManager:
    """国际化管理器"""
    
    def __init__(self, language: str = DEFAULT_LANGUAGE):
        self._language = language
        self._translations: Dict[str, Any] = {}
        self._load_translations()
    
    def _load_translations(self) -> None:
        """加载翻译文件"""
        lang_file = I18N_DIR / f"{self._language}_CN.json"
        
        if not lang_file.exists():
            lang_file = I18N_DIR / f"{self._language}_US.json"
        
        if not lang_file.exists():
            lang_file = I18N_DIR / f"{self._language}_DE.json"
        
        if lang_file.exists():
            try:
                with open(lang_file, "r", encoding="utf-8") as f:
                    self._translations = json.load(f)
                logger.info(f"已加载语言: {self._language}")
            except Exception as e:
                logger.warning(f"加载翻译失败: {e}")
                self._translations = {}
        else:
            logger.warning(f"未找到语言文件: {self._language}")
            self._translations = {}
    
    def set_language(self, language: str) -> None:
        """切换语言"""
        if language in SUPPORTED_LANGUAGES:
            self._language = language
            self._load_translations()
        else:
            logger.warning(f"不支持的语言: {language}")
    
    def get(self, key: str, default: str = "") -> str:
        """获取翻译文本（支持点号分隔的路径）"""
        keys = key.split(".")
        value = self._translations
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            
            if value is None:
                return default
        
        return str(value) if value else default
    
    def __call__(self, key: str, default: str = "") -> str:
        """快捷调用"""
        return self.get(key, default)


def get_i18n(language: str = DEFAULT_LANGUAGE) -> I18nManager:
    """获取国际化管理器实例"""
    return I18nManager(language)
