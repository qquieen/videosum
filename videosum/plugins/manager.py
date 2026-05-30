"""插件管理器"""

import logging
import importlib
from typing import Dict, List, Optional, Any
from pathlib import Path

from videosum.plugins.base import PluginBase

logger = logging.getLogger(__name__)


class PluginManager:
    """插件管理器"""
    
    PLUGIN_NAMESPACE = "videosummary.plugins"
    
    def __init__(self, plugin_dir: Optional[str] = None):
        """
        初始化
        
        Args:
            plugin_dir: 插件目录路径
        """
        if plugin_dir:
            self.plugin_dir = Path(plugin_dir)
        else:
            self.plugin_dir = Path.home() / ".videosummary" / "plugins"
        
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        self.plugins: Dict[str, PluginBase] = {}
    
    def discover_plugins(self) -> List[str]:
        """
        发现已安装的插件
        
        Returns:
            发现的插件名称列表
        """
        discovered = []
        
        # 方式1: 通过entry_points发现（推荐）
        try:
            import pkg_resources
            for ep in pkg_resources.iter_entry_points(self.PLUGIN_NAMESPACE):
                try:
                    plugin_class = ep.load()
                    plugin = plugin_class()
                    self.plugins[plugin.name] = plugin
                    discovered.append(plugin.name)
                    logger.info(f"发现插件: {plugin.name}")
                except Exception as e:
                    logger.warning(f"加载插件失败 {ep.name}: {e}")
        except ImportError:
            logger.debug("pkg_resources不可用，跳过entry_points发现")
        
        # 方式2: 扫描插件目录（备选）
        if self.plugin_dir.exists():
            for path in self.plugin_dir.glob("*/plugin.py"):
                try:
                    # 动态导入模块
                    spec = importlib.util.spec_from_file_location(
                        f"plugin_{path.parent.name}",
                        path
                    )
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        if hasattr(module, "register"):
                            plugin = module.register()
                            if plugin.name not in self.plugins:
                                self.plugins[plugin.name] = plugin
                                discovered.append(plugin.name)
                                logger.info(f"发现本地插件: {plugin.name}")
                except Exception as e:
                    logger.warning(f"加载本地插件失败 {path}: {e}")
        
        return discovered
    
    def get_plugin(self, name: str) -> Optional[PluginBase]:
        """
        获取插件实例
        
        Args:
            name: 插件名称
        
        Returns:
            插件实例，如果不存在则返回None
        """
        return self.plugins.get(name)
    
    def initialize_plugin(
        self,
        name: str,
        config: Dict[str, Any]
    ) -> bool:
        """
        初始化插件
        
        Args:
            name: 插件名称
            config: 插件配置
        
        Returns:
            是否初始化成功
        """
        plugin = self.plugins.get(name)
        if not plugin:
            logger.warning(f"插件不存在: {name}")
            return False
        
        try:
            return plugin.initialize(config)
        except Exception as e:
            logger.error(f"初始化插件失败 {name}: {e}")
            return False
    
    def install_plugin(self, name: str) -> bool:
        """
        安装插件依赖
        
        Args:
            name: 插件名称
        
        Returns:
            是否安装成功
        """
        plugin = self.plugins.get(name)
        if not plugin:
            logger.warning(f"插件不存在: {name}")
            return False
        
        try:
            return plugin.install()
        except Exception as e:
            logger.error(f"安装插件失败 {name}: {e}")
            return False
    
    def cleanup_plugin(self, name: str):
        """
        清理插件
        
        Args:
            name: 插件名称
        """
        plugin = self.plugins.get(name)
        if plugin:
            try:
                plugin.cleanup()
            except Exception as e:
                logger.warning(f"清理插件失败 {name}: {e}")
    
    def list_plugins(self) -> List[Dict[str, str]]:
        """
        列出所有插件
        
        Returns:
            插件信息列表 [{"name": str, "version": str, "description": str}]
        """
        return [
            {
                "name": p.name,
                "version": p.version,
                "description": p.description
            }
            for p in self.plugins.values()
        ]
