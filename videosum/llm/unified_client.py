from typing import List, Dict, Optional, AsyncIterator
import logging
import time

from videosum.models import LLMProvider
from videosum.llm.base import LLMEngine, LLMError

logger = logging.getLogger(__name__)

# 供应商配置
PROVIDER_CONFIGS = {
    LLMProvider.DEEPSEEK: {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "context_length": 64000,
    },
    LLMProvider.QWEN: {
        "name": "Qwen",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-plus",
        "context_length": 128000,
    },
    LLMProvider.KIMI: {
        "name": "Kimi",
        "base_url": "https://api.moonshot.cn/v1",
        "default_model": "moonshot-v1-128k",
        "context_length": 128000,
    },
    LLMProvider.GLM: {
        "name": "GLM",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "default_model": "glm-4-plus",
        "context_length": 128000,
    },
    LLMProvider.OPENAI: {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4.1-mini",
        "context_length": 128000,
    },
    LLMProvider.OLLAMA: {
        "name": "Ollama",
        "base_url": "http://localhost:11434/v1",
        "default_model": "qwen2.5:7b",
        "context_length": 8192,
    },
}


class UnifiedLLMClient(LLMEngine):
    """统一OpenAI兼容客户端"""
    
    def __init__(
        self,
        provider: LLMProvider,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4000
    ):
        self._provider = provider
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._client = None
        
        config = PROVIDER_CONFIGS.get(provider, {})
        self._config_name = config.get("name", provider.value)
        self._config_base_url = config.get("base_url", "")
        self._config_context_length = config.get("context_length", 8192)
    
    @property
    def provider(self) -> LLMProvider:
        return self._provider
    
    @property
    def name(self) -> str:
        model = self._model or PROVIDER_CONFIGS.get(self._provider, {}).get("default_model", "unknown")
        return f"{self._config_name} ({model})"
    
    @property
    def context_length(self) -> int:
        return self._config_context_length
    
    def _get_client(self):
        """获取OpenAI客户端"""
        if self._client is not None:
            return self._client
        
        try:
            from openai import OpenAI
        except ImportError:
            raise LLMError("openai未安装。请运行: pip install openai")
        
        base_url = self._base_url or self._config_base_url
        api_key = self._api_key or "ollama"  # Ollama不需要真实key
        
        self._client = OpenAI(
            base_url=base_url,
            api_key=api_key
        )
        return self._client
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> str:
        """生成文本"""
        client = self._get_client()
        model = self._model or PROVIDER_CONFIGS.get(self._provider, {}).get("default_model")
        
        if not model:
            raise LLMError("未指定模型")
        
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature or self._temperature,
                max_tokens=max_tokens or self._max_tokens,
                stream=stream
            )
            
            if stream:
                # 流式输出需要单独处理
                return response
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise LLMError(f"生成失败: {str(e)}")
    
    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AsyncIterator[str]:
        """流式生成文本"""
        client = self._get_client()
        model = self._model or PROVIDER_CONFIGS.get(self._provider, {}).get("default_model")
        
        if not model:
            raise LLMError("未指定模型")
        
        try:
            stream = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature or self._temperature,
                max_tokens=max_tokens or self._max_tokens,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            raise LLMError(f"流式生成失败: {str(e)}")
    
    def count_tokens(self, text: str) -> int:
        """计算token数量（估算）"""
        # 简单估算：中文约1.5字/token，英文约4字符/token
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        
        return int(chinese_chars / 1.5 + other_chars / 4)
    
    def is_available(self) -> bool:
        """检查是否可用"""
        try:
            from openai import OpenAI
            return True
        except ImportError:
            return False
