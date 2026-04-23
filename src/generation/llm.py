from __future__ import annotations

from collections.abc import Callable

from src.common.ollama_client import OllamaClient


class OllamaGenerator:
    def __init__(self, model: str, base_url: str, timeout: int = 300) -> None:
        self.client = OllamaClient(model=model, base_url=base_url, timeout=timeout)

    def generate(
        self,
        prompt: str,
        *,
        stream: bool = False,
        on_chunk: Callable[[str], None] | None = None,
    ) -> str:
        if stream:
            return self.client.generate_stream(prompt, on_chunk=on_chunk)
        return self.client.generate(prompt)


class LangChainGenerator:
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.0, max_tokens: int = 500) -> None:
        from langchain_openai import ChatOpenAI  # noqa: PLC0415

        self.llm = ChatOpenAI(model=model, temperature=temperature, max_tokens=max_tokens)

    def generate(self, prompt: str) -> str:
        response = self.llm.invoke(prompt)
        return response.content if hasattr(response, "content") else str(response)
