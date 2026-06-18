from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.generation.base import BaseGenerator


class OpenAIGenerator(BaseGenerator):
    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.1,
        max_tokens: int = 800,
    ) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required when GENERATION_PROVIDER=openai.")
        try:
            from openai import OpenAI  # noqa: PLC0415
        except ImportError as exc:
            raise RuntimeError("The official OpenAI SDK is required. Install the `openai` package.") from exc

        self._client = OpenAI(api_key=api_key)
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self.provider = "openai"
        self.model = model
        self.last_usage: dict[str, Any] | None = None

    def generate(
        self,
        prompt: str,
        *,
        stream: bool = False,
        on_chunk: Callable[[str], None] | None = None,
        options: dict[str, float | int] | None = None,
    ) -> str:
        request_options = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }
        if options:
            request_options.update(options)
        self.last_usage = None

        if not stream:
            response = self._client.chat.completions.create(**request_options)
            self.last_usage = self._usage_to_dict(getattr(response, "usage", None))
            return response.choices[0].message.content or ""

        chunks: list[str] = []
        response_stream = self._client.chat.completions.create(
            **request_options,
            stream=True,
            stream_options={"include_usage": True},
        )
        for chunk in response_stream:
            usage = self._usage_to_dict(getattr(chunk, "usage", None))
            if usage is not None:
                self.last_usage = usage
            content = chunk.choices[0].delta.content or ""
            if not content:
                continue
            chunks.append(content)
            if on_chunk is not None:
                on_chunk(content)
        return "".join(chunks)

    @staticmethod
    def _usage_to_dict(usage: Any) -> dict[str, Any] | None:
        """Convert OpenAI SDK usage objects into plain dictionaries."""
        if usage is None:
            return None
        if isinstance(usage, dict):
            return dict(usage)
        if hasattr(usage, "model_dump"):
            return dict(usage.model_dump())
        return {
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
        }
