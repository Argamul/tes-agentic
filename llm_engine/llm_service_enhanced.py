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
        self.api_key = os.getenv("OPENAI_API_KEY")
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.client = ChatOpenAI(
            openai_api_key=self.api_key,
            model_name=self.default_model,
            temperature=float(os.getenv("TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("MAX_TOKENS", "1000"))
        )
    
    async def generate_text(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        """Generate text using OpenAI"""
        try:
            model_name = model or self.default_model
            messages = [HumanMessage(content=prompt)]
            
            # Create client with specific model
            client = ChatOpenAI(
                openai_api_key=self.api_key,
                model_name=model_name,
                temperature=kwargs.get("temperature", float(os.getenv("TEMPERATURE", "0.7"))),
                max_tokens=kwargs.get("max_tokens", int(os.getenv("MAX_TOKENS", "1000")))
            )
            
            response = await client.agenerate([messages])
            return response.generations[0][0].text
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            raise
    
    async def chat_completion(self, messages: List[BaseMessage], model: Optional[str] = None, **kwargs) -> str:
        """Generate chat completion using OpenAI"""
        try:
            model_name = model or self.default_model
            
            client = ChatOpenAI(
                openai_api_key=self.api_key,
                model_name=model_name,
                temperature=kwargs.get("temperature", float(os.getenv("TEMPERATURE", "0.7"))),
                max_tokens=kwargs.get("max_tokens", int(os.getenv("MAX_TOKENS", "1000")))
            )
            
            response = await client.agenerate([messages])
            return response.generations[0][0].text
        except Exception as e:
            logger.error(f"OpenAI chat completion failed: {e}")
            raise
    
    def get_available_models(self) -> Dict[str, str]:
        """Get available OpenAI models"""
        return {
            "gpt-5-mini": "GPT-5-mini"
        }

class AnthropicProvider(BaseLLMProvider):
    """Anthropic-specific implementation"""
    
    def __init__(self):
        self.default_model = os.getenv("ANTHROPIC_DEFAULT_MODEL", "claude-3-sonnet-20240229")
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required")
        
        self.client = ChatAnthropic(
            anthropic_api_key=self.api_key,
            model_name=self.default_model,
            temperature=float(os.getenv("TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("MAX_TOKENS", "1000"))
        )
    
    async def generate_text(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        """Generate text using Anthropic"""
        try:
            model_name = model or self.default_model
            messages = [HumanMessage(content=prompt)]
            
            client = ChatAnthropic(
                anthropic_api_key=self.api_key,
                model_name=model_name,
                temperature=kwargs.get("temperature", float(os.getenv("TEMPERATURE", "0.7"))),
                max_tokens=kwargs.get("max_tokens", int(os.getenv("MAX_TOKENS", "1000")))
            )
            
            response = await client.agenerate([messages])
            return response.generations[0][0].text
        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}")
            raise
    
    async def chat_completion(self, messages: List[BaseMessage], model: Optional[str] = None, **kwargs) -> str:
        """Generate chat completion using Anthropic"""
        try:
            model_name = model or self.default_model
            
            client = ChatAnthropic(
                anthropic_api_key=self.api_key,
                model_name=model_name,
                temperature=kwargs.get("temperature", float(os.getenv("TEMPERATURE", "0.7"))),
                max_tokens=kwargs.get("max_tokens", int(os.getenv("MAX_TOKENS", "1000")))
            )
            
            response = await client.agenerate([messages])
            return response.generations[0][0].text
        except Exception as e:
            logger.error(f"Anthropic chat completion failed: {e}")
            raise
    
    def get_available_models(self) -> Dict[str, str]:
        """Get available Anthropic models"""
        return {
            "claude-3-haiku-20240307": "Claude 3 Haiku"
        }

class LlamaProvider(BaseLLMProvider):
    """Local LLaMA implementation"""
    
    def __init__(self):
        self.model_path = os.getenv("LLAMA_MODEL_PATH", "/app/models/llama-2-7b-chat.gguf")
        self.n_ctx = int(os.getenv("LLAMA_N_CTX", "2048"))
        self.n_gpu_layers = int(os.getenv("LLAMA_N_GPU_LAYERS", "0"))
        
        if not os.path.exists(self.model_path):
            raise ValueError(f"LLaMA model not found at {self.model_path}")
        
        self.client = LlamaCpp(
            model_path=self.model_path,
            n_ctx=self.n_ctx,
            n_gpu_layers=self.n_gpu_layers,
            temperature=float(os.getenv("TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("MAX_TOKENS", "1000"))
        )
    
    async def generate_text(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        """Generate text using local LLaMA"""
        try:
            response = await self.client.agenerate([prompt])
            return response.generations[0][0].text
        except Exception as e:
            logger.error(f"LLaMA generation failed: {e}")
            raise
    
    async def chat_completion(self, messages: List[BaseMessage], model: Optional[str] = None, **kwargs) -> str:
        """Generate chat completion using local LLaMA"""
        try:
            # Convert messages to prompt format
            prompt = self._messages_to_prompt(messages)
            response = await self.client.agenerate([prompt])
            return response.generations[0][0].text
        except Exception as e:
            logger.error(f"LLaMA chat completion failed: {e}")
            raise
    
    def _messages_to_prompt(self, messages: List[BaseMessage]) -> str:
        """Convert messages to LLaMA prompt format"""
        prompt = ""
        for message in messages:
            if isinstance(message, SystemMessage):
                prompt += f"System: {message.content}\n"
            elif isinstance(message, HumanMessage):
                prompt += f"Human: {message.content}\n"
            else:
                prompt += f"Assistant: {message.content}\n"
        prompt += "Assistant: "
        return prompt
    
    def get_available_models(self) -> Dict[str, str]:
        """Get available LLaMA models"""
        return {
            "llama-2-7b-chat": "LLaMA 2 7B Chat",
            "llama-2-13b-chat": "LLaMA 2 13B Chat",
            "llama-2-70b-chat": "LLaMA 2 70B Chat"
        }

class LLMService:
    """Main LLM service that manages multiple providers with fallback and Redis caching"""
    
    def __init__(self):
        self.providers = {}
        self.fallback_order = os.getenv("LLM_PROVIDER_FALLBACK_ORDER", "openai,anthropic,llama").split(",")
        self.cache_enabled = os.getenv("REDIS_CACHE_ENABLED", "true").lower() == "true"
        self.cache_ttl = int(os.getenv("REDIS_CACHE_TTL_SECONDS", "600"))
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize available LLM providers"""
        try:
            self.providers[LLMProvider.OPENAI] = OpenAIProvider()
            logger.info("OpenAI provider initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI provider: {e}")
        
        try:
            self.providers[LLMProvider.ANTHROPIC] = AnthropicProvider()
            logger.info("Anthropic provider initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Anthropic provider: {e}")
        
        try:
            self.providers[LLMProvider.LLAMA] = LlamaProvider()
            logger.info("Llama provider initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Llama provider: {e}")
    
    async def generate_text(self, prompt: str, model: Optional[str] = None, **kwargs) -> str:
        """Generate text using the best available provider with Redis caching"""
        # Check cache first if enabled
        if self.cache_enabled:
            cache_key = make_cache_key("llm_generate", prompt, model, kwargs)
            cached_result = await cache_get_text(cache_key)
            if cached_result:
                logger.info(f"Cache hit for LLM generation: {cache_key[:20]}...")
                return cached_result
        
        # Try providers in fallback order
        last_exception = None
        for provider_name in self.fallback_order:
            provider_name = provider_name.strip().lower()
            try:
                provider_enum = LLMProvider(provider_name)
                if provider_enum in self.providers:
                    result = await self.providers[provider_enum].generate_text(prompt, model, **kwargs)
                    
                    # Cache the result if enabled
                    if self.cache_enabled:
                        await cache_set_text(cache_key, result, self.cache_ttl)
                        logger.info(f"Cached LLM generation result for key: {cache_key[:20]}...")
                    
                    logger.info(f"Generated text using {provider_name} provider")
                    return result
            except Exception as e:
                logger.warning(f"Provider {provider_name} failed: {e}")
                last_exception = e
                continue
        
        raise Exception(f"All LLM providers failed. Last error: {last_exception}")
    
    async def chat_completion(self, messages: List[BaseMessage], model: Optional[str] = None, **kwargs) -> str:
        """Generate chat completion using the best available provider with Redis caching"""
        # Check cache first if enabled
        if self.cache_enabled:
            cache_key = make_cache_key("llm_chat", str(messages), model, kwargs)
            cached_result = await cache_get_text(cache_key)
            if cached_result:
                logger.info(f"Cache hit for LLM chat: {cache_key[:20]}...")
                return cached_result
        
        # Try providers in fallback order
        last_exception = None
        for provider_name in self.fallback_order:
            provider_name = provider_name.strip().lower()
            try:
                provider_enum = LLMProvider(provider_name)
                if provider_enum in self.providers:
                    result = await self.providers[provider_enum].chat_completion(messages, model, **kwargs)
                    
                    # Cache the result if enabled
                    if self.cache_enabled:
                        await cache_set_text(cache_key, result, self.cache_ttl)
                        logger.info(f"Cached LLM chat result for key: {cache_key[:20]}...")
                    
                    logger.info(f"Generated chat completion using {provider_name} provider")
                    return result
            except Exception as e:
                logger.warning(f"Provider {provider_name} failed: {e}")
                last_exception = e
                continue
        
        raise Exception(f"All LLM providers failed. Last error: {last_exception}")
    
    async def generate_with_metadata(self, prompt: str, model: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Generate text with metadata including cache status and provider used"""
        start_time = asyncio.get_event_loop().time()
        
        # Check cache first if enabled
        cache_hit = False
        if self.cache_enabled:
            cache_key = make_cache_key("llm_generate", prompt, model, kwargs)
            cached_result = await cache_get_text(cache_key)
            if cached_result:
                cache_hit = True
                end_time = asyncio.get_event_loop().time()
                return {
                    "text": cached_result,
                    "cache_hit": True,
                    "provider": "cache",
                    "model": model,
                    "response_time": end_time - start_time,
                    "cached_at": cache_key
                }
        
        # Try providers in fallback order
        last_exception = None
        for provider_name in self.fallback_order:
            provider_name = provider_name.strip().lower()
            try:
                provider_enum = LLMProvider(provider_name)
                if provider_enum in self.providers:
                    result = await self.providers[provider_enum].generate_text(prompt, model, **kwargs)
                    
                    # Cache the result if enabled
                    if self.cache_enabled:
                        await cache_set_text(cache_key, result, self.cache_ttl)
                    
                    end_time = asyncio.get_event_loop().time()
                    return {
                        "text": result,
                        "cache_hit": False,
                        "provider": provider_name,
                        "model": model,
                        "response_time": end_time - start_time,
                        "cached": self.cache_enabled
                    }
            except Exception as e:
                logger.warning(f"Provider {provider_name} failed: {e}")
                last_exception = e
                continue
        
        raise Exception(f"All LLM providers failed. Last error: {last_exception}")
    
    def get_available_models(self) -> Dict[str, List[str]]:
        """Get available models from all providers"""
        models = {}
        for provider_enum, provider in self.providers.items():
            try:
                models[provider_enum.value] = list(provider.get_available_models().keys())
            except Exception as e:
                logger.warning(f"Failed to get models from {provider_enum.value}: {e}")
        return models
    
    async def clear_cache(self, pattern: str = "llm_*") -> int:
        """Clear cache entries matching pattern"""
        if not self.cache_enabled:
            return 0
        
        from cache.redis_cache import get_redis_client
        client = get_redis_client()
        if not client:
            return 0
        
        try:
            keys = await client.keys(pattern)
            if keys:
                deleted = await client.delete(*keys)
                logger.info(f"Cleared {deleted} cache entries matching pattern: {pattern}")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.cache_enabled:
            return {"enabled": False}
        
        from cache.redis_cache import get_redis_client
        client = get_redis_client()
        if not client:
            return {"enabled": True, "connected": False}
        
        try:
            info = await client.info()
            return {
                "enabled": True,
                "connected": True,
                "used_memory": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": info.get("keyspace_hits", 0) / max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0))
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"enabled": True, "connected": False, "error": str(e)}



