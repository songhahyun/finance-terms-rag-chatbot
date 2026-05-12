from __future__ import annotations

from collections.abc import Callable

from src.common.ollama_client import OllamaClient


class OllamaGenerator:
    def __init__(
        self,
        model: str,
        base_url: str,
        timeout: int = 300,
        temperature: float = 0.2,
        top_p: float = 0.85,
        repeat_penalty: float = 1.1,
        keep_alive: str | int = -1,
    ) -> None:
        """Create an Ollama-backed text generator wrapper.
        Store a configured low-level client for later prompt execution."""
        self.client = OllamaClient(
            model=model,
            base_url=base_url,
            timeout=timeout,
            temperature=temperature,
            top_p=top_p,
            repeat_penalty=repeat_penalty,
            keep_alive=keep_alive,
        )

    def generate(
        self,
        prompt: str,
        *,
        stream: bool = False,
        on_chunk: Callable[[str], None] | None = None,
    ) -> str:
        """Generate text from a prompt with optional streaming.
        Delegate either to the normal or streaming client method."""
        if stream:
            return self.client.generate_stream(prompt, on_chunk=on_chunk)
        return self.client.generate(prompt)


class LangChainGenerator:
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.0, max_tokens: int = 500) -> None:
        """Create a LangChain chat model wrapper.
        Configure the target OpenAI-compatible model and token limits."""
        from langchain_openai import ChatOpenAI  # noqa: PLC0415

        self.llm = ChatOpenAI(model=model, temperature=temperature, max_tokens=max_tokens)

    def generate(self, prompt: str) -> str:
        """Run a prompt through the wrapped chat model.
        Return plain text regardless of the response object shape."""
        response = self.llm.invoke(prompt)
        return response.content if hasattr(response, "content") else str(response)
