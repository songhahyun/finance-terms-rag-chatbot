from __future__ import annotations

import json
from collections.abc import Callable

import requests


class OllamaClient:
    def __init__(
        self,
        model: str = "qwen2.5:7b",
        base_url: str = "http://localhost:11434",
        timeout: int = 300,
        temperature: float = 0.2,
        top_p: float = 0.85,
        repeat_penalty: float = 1.1,
        keep_alive: str = "30m",
    ) -> None:
        """Configure a lightweight client for the Ollama HTTP API.
        Store model selection, base URL, timeout, and generation defaults."""
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.keep_alive = keep_alive
        self.options = {
            "temperature": temperature,
            "top_p": top_p,
            "repeat_penalty": repeat_penalty,
        }

    def _options(self, num_predict: int) -> dict[str, float | int]:
        """Build per-request Ollama generation options."""
        return {**self.options, "num_predict": num_predict}

    def generate(self, prompt: str, *, num_predict: int = 500) -> str:
        """Send a non-streaming text generation request to Ollama.
        Return the stripped response body from the API payload."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": self._options(num_predict),
        }
        response = requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        return response.json().get("response", "").strip()

    def generate_stream(
        self,
        prompt: str,
        *,
        num_predict: int = 500,
        on_chunk: Callable[[str], None] | None = None,
    ) -> str:
        """Stream generated text from Ollama while collecting the full output.
        Forward each chunk to the optional callback as it arrives."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "keep_alive": self.keep_alive,
            "options": self._options(num_predict),
        }
        parts: list[str] = []
        with requests.post(url, json=payload, timeout=self.timeout, stream=True) as response:
            response.raise_for_status()
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                packet = json.loads(line)
                text = str(packet.get("response", ""))
                if text:
                    parts.append(text)
                    if on_chunk is not None:
                        on_chunk(text)
                if packet.get("done"):
                    break
        return "".join(parts).strip()

    def chat(self, messages: list[dict], *, num_predict: int = 500) -> str:
        """Send a chat-style request to Ollama.
        Return the assistant message content from the JSON response."""
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "keep_alive": self.keep_alive,
            "options": self._options(num_predict),
        }
        response = requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        return response.json()["message"]["content"].strip()
