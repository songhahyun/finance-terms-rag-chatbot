from __future__ import annotations

import json
from collections.abc import Callable

import requests


class OllamaClient:
    def __init__(self, model: str = "qwen2.5:7b", base_url: str = "http://localhost:11434", timeout: int = 300) -> None:
        """Configure a lightweight client for the Ollama HTTP API.
        Store model selection, base URL, and timeout defaults."""
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def generate(self, prompt: str, *, num_predict: int = 500) -> str:
        """Send a non-streaming text generation request to Ollama.
        Return the stripped response body from the API payload."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": num_predict},
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
            "options": {"num_predict": num_predict},
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
            "options": {"num_predict": num_predict},
        }
        response = requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        return response.json()["message"]["content"].strip()
