from __future__ import annotations

from typing import Any

from src.generation.base import BaseGenerator
from src.generation.ollama import OllamaGenerator
from src.generation.openai_provider import OpenAIGenerator


def build_generator(settings: Any) -> BaseGenerator:
    provider = str(getattr(settings, "generation_provider", "ollama")).lower()
    if provider == "ollama":
        return OllamaGenerator(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            timeout=settings.ollama_timeout,
            temperature=settings.ollama_temperature,
            top_p=settings.ollama_top_p,
            repeat_penalty=settings.ollama_repeat_penalty,
            keep_alive=settings.ollama_keep_alive,
        )
    if provider == "openai":
        return OpenAIGenerator(
            api_key=getattr(settings, "openai_api_key", ""),
            model=getattr(settings, "openai_generation_model", "gpt-4o-mini"),
            temperature=getattr(settings, "generation_temperature", 0.1),
            max_tokens=getattr(settings, "generation_max_tokens", 800),
        )
    raise ValueError("GENERATION_PROVIDER must be one of: ollama, openai.")
