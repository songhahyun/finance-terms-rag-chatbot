from __future__ import annotations

from collections.abc import Callable

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

        if not stream:
            response = self._client.chat.completions.create(**request_options)
            return response.choices[0].message.content or ""

        chunks: list[str] = []
        response_stream = self._client.chat.completions.create(**request_options, stream=True)
        for chunk in response_stream:
            content = chunk.choices[0].delta.content or ""
            if not content:
                continue
            chunks.append(content)
            if on_chunk is not None:
                on_chunk(content)
        return "".join(chunks)
