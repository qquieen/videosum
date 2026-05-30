"""联网搜索API模块"""

import logging
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class WebSearchError(Exception):
    """联网搜索错误"""
    pass


class SearchProvider(ABC):
    """搜索供应商基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @abstractmethod
    def search(self, query: str, num_results: int = 5) -> List[Dict]:
        """
        搜索
        
        Args:
            query: 搜索查询
            num_results: 返回结果数量
        
        Returns:
            搜索结果列表 [{"title": str, "url": str, "snippet": str}]
        """
        pass


class TavilySearch(SearchProvider):
    """Tavily搜索（推荐）"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    @property
    def name(self) -> str:
        return "Tavily"
    
    def search(self, query: str, num_results: int = 5) -> List[Dict]:
        import requests
        
        url = "https://api.tavily.com/search"
        
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": num_results,
            "include_answer": True
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for item in data.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("content", "")
                })
            
            return results
            
        except Exception as e:
            raise WebSearchError(f"Tavily搜索失败: {e}")


class SerpAPISearch(SearchProvider):
    """SerpAPI搜索"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    @property
    def name(self) -> str:
        return "SerpAPI"
    
    def search(self, query: str, num_results: int = 5) -> List[Dict]:
        import requests
        
        url = "https://serpapi.com/search"
        
        params = {
            "api_key": self.api_key,
            "q": query,
            "num": num_results,
            "engine": "google"
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            for item in data.get("organic_results", [])[:num_results]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", "")
                })
            
            return results
            
        except Exception as e:
            raise WebSearchError(f"SerpAPI搜索失败: {e}")


class WebSearchAPI:
    """联网搜索API"""
    
    def __init__(self, provider: str = "tavily", api_key: str = ""):
        """
        初始化
        
        Args:
            provider: 搜索供应商 (tavily, serpapi)
            api_key: API密钥
        """
        self._provider = self._create_provider(provider, api_key)
    
    def _create_provider(self, provider: str, api_key: str) -> SearchProvider:
        """创建搜索供应商实例"""
        providers = {
            "tavily": TavilySearch,
            "serpapi": SerpAPISearch,
        }
        
        provider_class = providers.get(provider)
        if not provider_class:
            raise WebSearchError(f"不支持的搜索供应商: {provider}")
        
        return provider_class(api_key)
    
    def search(self, query: str, num_results: int = 5) -> List[Dict]:
        """
        搜索
        
        Args:
            query: 搜索查询
            num_results: 返回结果数量
        
        Returns:
            搜索结果列表
        """
        return self._provider.search(query, num_results)
    
    def search_for_context(
        self,
        query: str,
        num_results: int = 3
    ) -> str:
        """
        搜索并返回上下文文本（用于LLM）
        
        Args:
            query: 搜索查询
            num_results: 返回结果数量
        
        Returns:
            格式化的上下文文本
        """
        results = self.search(query, num_results)
        
        context_parts = []
        for i, result in enumerate(results, 1):
            context_parts.append(
                f"[{i}] {result['title']}\n"
                f"URL: {result['url']}\n"
                f"{result['snippet']}\n"
            )
        
        return "\n".join(context_parts)
