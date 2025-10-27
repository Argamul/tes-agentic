import os
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Type
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI, ChatAnthropic
from langchain.llms import LlamaCpp
from langchain.schema import HumanMessage, SystemMessage, BaseMessage
import logging
from enum import Enum
from cache.redis_cache import (
    make_cache_key,
    cache_get_text,
    cache_set_text,
    cache_get_json,
    cache_set_json,
)

# Load environment variables
load_dotenv()
logger = logging.getLogger(__name__)

class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LLAMA = "llama"

class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text from prompt"""
        pass
    
    @abstractmethod
    async def chat_completion(self, messages: List[BaseMessage], **kwargs) -> str:
        """Generate chat completion from messages"""
        pass
    
    @abstractmethod
    def get_available_models(self) -> Dict[str, str]:
        """Get available models for this provider"""
        pass

class OpenAIProvider(BaseLLMProvider):
    """OpenAI-specific implementation"""
    
    def __init__(self):
        self.default_model = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-3.5-turbo")
        self.fallback_model = os.getenv("OPENAI_FALLBACK_MODEL", "gpt-3.5-turbo-16k")
        self.client = ChatOpenAI(
            model_name=self.default_model,
            temperature=float(os.getenv("TEMPERATURE", 0.7)),
            max_tokens=int(os.getenv("MAX_TOKENS", 1000))
        )
        
    async def generate_text(self, prompt: str, **kwargs) -> str:
        try:
            messages = [HumanMessage(content=prompt)]
            response = await self.client.ainvoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"OpenAI generation error: {str(e)}")
            raise
            
    async def chat_completion(self, messages: List[BaseMessage], **kwargs) -> str:
        try:
            response = await self.client.ainvoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"OpenAI chat completion error: {str(e)}")
            raise
            
    def get_available_models(self) -> Dict[str, str]:
        return {
            "gpt-5-mini": "GPT-5-mini",
        }

class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude-specific implementation"""
    
    def __init__(self):
        self.default_model = os.getenv("CLAUDE_DEFAULT_MODEL", "claude-2.1")
        self.fallback_model = os.getenv("CLAUDE_FALLBACK_MODEL", "claude-instant-1.2")
        self.client = ChatAnthropic(
            model_name=self.default_model,
            temperature=float(os.getenv("TEMPERATURE", 0.7)),
            max_tokens=int(os.getenv("MAX_TOKENS", 1000))
        )
        
    async def generate_text(self, prompt: str, **kwargs) -> str:
        try:
            messages = [HumanMessage(content=prompt)]
            response = await self.client.ainvoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"Anthropic generation error: {str(e)}")
            raise
            
    async def chat_completion(self, messages: List[BaseMessage], **kwargs) -> str:
        try:
            response = await self.client.ainvoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"Anthropic chat completion error: {str(e)}")
            raise
            
    def get_available_models(self) -> Dict[str, str]:
        return {
            "claude-2.1": "Claude 2.1",
            "claude-instant-1.2": "Claude Instant 1.2"
        }

class LlamaProvider(BaseLLMProvider):
    """Local LLaMA model implementation"""
    
    def __init__(self):
        model_path = os.getenv("LLAMA_MODEL_PATH")
        if not model_path:
            raise ValueError("LLAMA_MODEL_PATH not set in environment")
            
        self.default_model = os.getenv("LLAMA_DEFAULT_MODEL", "llama-2-7b-chat")
        self.client = LlamaCpp(
            model_path=model_path,
            n_gpu_layers=int(os.getenv("LLAMA_N_GPU_LAYERS", 32)),
            n_threads=int(os.getenv("LLAMA_N_THREADS", 4)),
            temperature=float(os.getenv("TEMPERATURE", 0.7)),
            max_tokens=int(os.getenv("MAX_TOKENS", 1000))
        )
        
    async def generate_text(self, prompt: str, **kwargs) -> str:
        try:
            response = await self.client.ainvoke(prompt)
            return response
        except Exception as e:
            logger.error(f"LLaMA generation error: {str(e)}")
            raise
            
    async def chat_completion(self, messages: List[BaseMessage], **kwargs) -> str:
        try:
            # Convert messages to prompt format LLaMA expects
            prompt = "\n".join([f"{msg.type}: {msg.content}" for msg in messages])
            response = await self.client.ainvoke(prompt)
            return response
        except Exception as e:
            logger.error(f"LLaMA chat completion error: {str(e)}")
            raise
            
    def get_available_models(self) -> Dict[str, str]:
        return {
            "llama-2-7b-chat": "LLaMA 2 7B Chat",
            "llama-2-13b-chat": "LLaMA 2 13B Chat"
        }

class LLMService:
    """
    Service for handling Large Language Model operations with multiple providers and automatic fallback.
    Supports OpenAI, Anthropic (Claude), and local LLaMA models.
    """
    
    def __init__(self):
        # Initialize providers
        self.providers = {
            LLMProvider.OPENAI: OpenAIProvider(),
            LLMProvider.ANTHROPIC: AnthropicProvider(),
            LLMProvider.LLAMA: LlamaProvider()
        }
        
        # Set default provider from environment
        default_provider = os.getenv("DEFAULT_LLM_PROVIDER", "openai")
        self.default_provider = LLMProvider(default_provider)
        
        # Set fallback order from environment
        fallback_order = os.getenv("LLM_PROVIDER_FALLBACK_ORDER", "openai,anthropic,llama")
        self.fallback_order = [LLMProvider(p) for p in fallback_order.split(",")]
        
        # Set max retries
        self.max_retries = int(os.getenv("MAX_RETRIES", 3))
    
    def _get_next_provider(self, current_provider: LLMProvider) -> Optional[LLMProvider]:
        """Get next provider in fallback chain"""
        try:
            current_idx = self.fallback_order.index(current_provider)
            if current_idx + 1 < len(self.fallback_order):
                return self.fallback_order[current_idx + 1]
        except ValueError:
            pass
        return None
    
    async def _execute_with_fallback(self, operation: str, func, *args, **kwargs) -> str:
        """Execute operation with automatic provider fallback"""
        current_provider = kwargs.pop("provider", self.default_provider)
        retries = 0
        
        while retries < self.max_retries:
            try:
                provider_instance = self.providers[current_provider]
                return await getattr(provider_instance, func)(*args, **kwargs)
            except Exception as e:
                logger.error(f"{operation} failed with {current_provider.value}: {str(e)}")
                
                # Try next provider in fallback chain
                next_provider = self._get_next_provider(current_provider)
                if next_provider:
                    logger.info(f"Falling back to {next_provider.value}")
                    current_provider = next_provider
                    retries += 1
                else:
                    raise Exception(f"All providers failed for {operation}")
        
        raise Exception(f"Max retries ({self.max_retries}) exceeded for {operation}")
    
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """
        Generate text using configured LLM providers with automatic fallback.
        
        Args:
            prompt: The input prompt for text generation
            **kwargs: Additional arguments passed to provider
            
        Returns:
            Generated text response
        """
        # Redis cache (optional)
        if os.getenv("REDIS_CACHE_ENABLED", "true").lower() in {"1", "true", "yes"}:
            provider = kwargs.get("provider", self.default_provider)
            provider_name = getattr(provider, "value", str(provider))
            model_name = kwargs.get("model")
            cache_key = make_cache_key("llm:generate", prompt, {"provider": provider_name, "model": model_name})
            cached = await cache_get_text(cache_key)
            if cached is not None:
                return cached

        result = await self._execute_with_fallback(
            "Text generation",
            "generate_text",
            prompt,
            **kwargs
        )

        if os.getenv("REDIS_CACHE_ENABLED", "true").lower() in {"1", "true", "yes"}:
            try:
                provider = kwargs.get("provider", self.default_provider)
                provider_name = getattr(provider, "value", str(provider))
                model_name = kwargs.get("model")
                cache_key = make_cache_key("llm:generate", prompt, {"provider": provider_name, "model": model_name})
                await cache_set_text(cache_key, result)
            except Exception:
                pass
        return result
    
    async def chat_completion(self, messages: List[BaseMessage], **kwargs) -> str:
        """
        Perform chat completion with automatic provider fallback.
        
        Args:
            messages: List of chat messages
            **kwargs: Additional arguments passed to provider
            
        Returns:
            Chat completion response
        """
        # Redis cache (optional)
        if os.getenv("REDIS_CACHE_ENABLED", "true").lower() in {"1", "true", "yes"}:
            provider = kwargs.get("provider", self.default_provider)
            provider_name = getattr(provider, "value", str(provider))
            model_name = kwargs.get("model")
            serializable_messages = [{"type": getattr(m, "type", None), "content": getattr(m, "content", None)} for m in messages]
            cache_key = make_cache_key("llm:chat", serializable_messages, {"provider": provider_name, "model": model_name})
            cached = await cache_get_text(cache_key)
            if cached is not None:
                return cached

        result = await self._execute_with_fallback(
            "Chat completion",
            "chat_completion",
            messages,
            **kwargs
        )

        if os.getenv("REDIS_CACHE_ENABLED", "true").lower() in {"1", "true", "yes"}:
            try:
                provider = kwargs.get("provider", self.default_provider)
                provider_name = getattr(provider, "value", str(provider))
                model_name = kwargs.get("model")
                serializable_messages = [{"type": getattr(m, "type", None), "content": getattr(m, "content", None)} for m in messages]
                cache_key = make_cache_key("llm:chat", serializable_messages, {"provider": provider_name, "model": model_name})
                await cache_set_text(cache_key, result)
            except Exception:
                pass
        return result
    
    def get_available_models(self, provider: Optional[LLMProvider] = None) -> Dict[str, str]:
        """
        Get available models for specified provider or all providers.
        
        Args:
            provider: Optional specific provider to get models for
            
        Returns:
            Dictionary of model names and descriptions
        """
        if provider:
            return self.providers[provider].get_available_models()
        
        all_models = {}
        for provider_enum, provider_instance in self.providers.items():
            provider_models = provider_instance.get_available_models()
            all_models.update({
                f"{provider_enum.value}/{model}": desc
                for model, desc in provider_models.items()
            })
        return all_models
