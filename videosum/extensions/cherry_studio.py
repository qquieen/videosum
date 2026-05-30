"""Cherry Studio集成模块"""

import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class CherryStudioError(Exception):
    """Cherry Studio集成错误"""
    pass


class CherryStudioIntegration:
    """
    Cherry Studio集成
    
    Cherry Studio是一个开源的AI客户端，支持多种LLM供应商。
    本模块提供与Cherry Studio的集成功能：
    1. 读取Cherry Studio的配置
    2. 同步API密钥
    3. 导出/导入对话
    """
    
    # Cherry Studio配置文件路径（Windows）
    CONFIG_PATHS = {
        "windows": Path.home() / "AppData" / "Roaming" / "cherry-studio" / "config.json",
        "macos": Path.home() / "Library" / "Application Support" / "cherry-studio" / "config.json",
        "linux": Path.home() / ".config" / "cherry-studio" / "config.json",
    }
    
    def __init__(self):
        self._config: Optional[Dict[str, Any]] = None
    
    def find_config_path(self) -> Optional[Path]:
        """查找Cherry Studio配置文件"""
        import platform
        
        system = platform.system().lower()
        config_path = self.CONFIG_PATHS.get(system)
        
        if config_path and config_path.exists():
            return config_path
        
        # 尝试所有路径
        for path in self.CONFIG_PATHS.values():
            if path.exists():
                return path
        
        return None
    
    def load_config(self) -> Dict[str, Any]:
        """加载Cherry Studio配置"""
        config_path = self.find_config_path()
        
        if not config_path:
            raise CherryStudioError("未找到Cherry Studio配置文件")
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self._config = json.load(f)
            
            logger.info(f"已加载Cherry Studio配置: {config_path}")
            return self._config
            
        except Exception as e:
            raise CherryStudioError(f"加载配置失败: {e}")
    
    def get_api_keys(self) -> Dict[str, str]:
        """
        获取Cherry Studio中配置的API密钥
        
        Returns:
            API密钥字典 {"provider": "api_key"}
        """
        if not self._config:
            self.load_config()
        
        api_keys = {}
        
        # Cherry Studio的配置结构可能变化，这里尝试多种可能的格式
        providers = self._config.get("providers", {})
        
        for provider_name, provider_config in providers.items():
            if isinstance(provider_config, dict):
                api_key = provider_config.get("apiKey", "")
                if api_key:
                    api_keys[provider_name] = api_key
        
        return api_keys
    
    def sync_to_videosum(self, config_manager) -> bool:
        """
        同步Cherry Studio的API密钥到VideoSum配置
        
        Args:
            config_manager: VideoSum配置管理器
        
        Returns:
            是否同步成功
        """
        try:
            api_keys = self.get_api_keys()
            
            # 映射Cherry Studio供应商名到VideoSum供应商名
            provider_map = {
                "openai": "openai",
                "deepseek": "deepseek",
                "moonshot": "kimi",
                "zhipu": "glm",
                "qwen": "qwen",
                "anthropic": "anthropic",
                "google": "google",
            }
            
            synced = 0
            for cs_provider, vs_provider in provider_map.items():
                if cs_provider in api_keys:
                    config_manager.set(
                        f"llm.{vs_provider}.api_key",
                        api_keys[cs_provider]
                    )
                    synced += 1
                    logger.info(f"同步API密钥: {cs_provider} -> {vs_provider}")
            
            if synced > 0:
                config_manager.save()
                logger.info(f"同步完成，共同步 {synced} 个供应商")
            
            return synced > 0
            
        except Exception as e:
            logger.error(f"同步失败: {e}")
            return False
    
    def export_conversations(
        self,
        output_path: str,
        conversations: Optional[List[Dict]] = None
    ) -> bool:
        """
        导出对话记录
        
        Args:
            output_path: 输出文件路径
            conversations: 对话记录列表
        
        Returns:
            是否导出成功
        """
        try:
            if conversations is None:
                conversations = []
            
            export_data = {
                "format": "videosum",
                "version": "1.0",
                "conversations": conversations
            }
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"导出对话记录: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出失败: {e}")
            return False
    
    def import_conversations(self, input_path: str) -> List[Dict]:
        """
        导入对话记录
        
        Args:
            input_path: 输入文件路径
        
        Returns:
            对话记录列表
        """
        try:
            with open(input_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            conversations = data.get("conversations", [])
            logger.info(f"导入对话记录: {len(conversations)} 条")
            
            return conversations
            
        except Exception as e:
            logger.error(f"导入失败: {e}")
            return []
