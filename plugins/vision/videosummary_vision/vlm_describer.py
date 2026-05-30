"""VLM描述模块"""

import logging
from typing import Optional
from pathlib import Path
import base64
import subprocess
import json

logger = logging.getLogger(__name__)


class VLMDescriberError(Exception):
    """VLM描述错误"""
    pass


class VLMDescriber:
    """VLM描述器（使用Ollama + LLaVA）"""
    
    def __init__(
        self,
        model: str = "llava:7b",
        base_url: str = "http://localhost:11434"
    ):
        """
        初始化
        
        Args:
            model: VLM模型名称
            base_url: Ollama API地址
        """
        self.model = model
        self.base_url = base_url
    
    def describe(
        self,
        frame_path: str,
        prompt: str = "请详细描述这张图片的内容，包括场景、物体、人物、文字等信息。"
    ) -> str:
        """
        描述图片内容
        
        Args:
            frame_path: 图片文件路径
            prompt: 描述提示词
        
        Returns:
            描述文本
        """
        frame_file = Path(frame_path)
        
        if not frame_file.exists():
            raise VLMDescriberError(f"图片文件不存在: {frame_path}")
        
        # 检查Ollama是否运行
        if not self._check_ollama():
            raise VLMDescriberError("Ollama未运行。请先启动Ollama: ollama serve")
        
        # 检查模型是否可用
        if not self._check_model():
            raise VLMDescriberError(f"模型 {self.model} 未安装。请运行: ollama pull {self.model}")
        
        # 读取图片并编码
        image_base64 = self._encode_image(frame_path)
        
        # 调用Ollama API
        description = self._call_ollama(image_base64, prompt)
        
        return description
    
    def _check_ollama(self) -> bool:
        """检查Ollama是否运行"""
        try:
            result = subprocess.run(
                ["curl", "-s", f"{self.base_url}/api/tags"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _check_model(self) -> bool:
        """检查模型是否可用"""
        try:
            result = subprocess.run(
                ["curl", "-s", f"{self.base_url}/api/tags"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                models = [m.get("name", "") for m in data.get("models", [])]
                return any(self.model in m for m in models)
            
            return False
            
        except Exception:
            return False
    
    def _encode_image(self, image_path: str) -> str:
        """将图片编码为base64"""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    
    def _call_ollama(self, image_base64: str, prompt: str) -> str:
        """调用Ollama API"""
        import requests
        
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [image_base64],
            "stream": False
        }
        
        try:
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "")
            
        except requests.exceptions.Timeout:
            raise VLMDescriberError("VLM描述超时")
        except Exception as e:
            raise VLMDescriberError(f"VLM描述失败: {e}")
    
    def describe_batch(
        self,
        frame_paths: list,
        prompt: str = "请详细描述这张图片的内容。"
    ) -> list:
        """
        批量描述图片
        
        Args:
            frame_paths: 图片路径列表
            prompt: 描述提示词
        
        Returns:
            描述文本列表
        """
        descriptions = []
        
        for i, path in enumerate(frame_paths):
            try:
                desc = self.describe(path, prompt)
                descriptions.append(desc)
                logger.info(f"描述完成 {i+1}/{len(frame_paths)}")
            except Exception as e:
                logger.warning(f"描述失败 {path}: {e}")
                descriptions.append(f"描述失败: {str(e)}")
        
        return descriptions
