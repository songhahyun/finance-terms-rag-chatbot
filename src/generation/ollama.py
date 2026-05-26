from __future__ import annotations

from collections.abc import Callable

from src.common.ollama_client import OllamaClient
from src.generation.base import BaseGenerator


class OllamaGenerator(BaseGenerator):
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
        options: dict[str, float | int] | None = None,
    ) -> str:
        """Generate text from a prompt with optional streaming.
        Delegate either to the normal or streaming client method."""
        if stream:
            return self.client.generate_stream(prompt, on_chunk=on_chunk, options=options)
        return self.client.generate(prompt, options=options)
