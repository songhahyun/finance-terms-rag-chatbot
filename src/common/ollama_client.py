from __future__ import annotations

import json
from collections.abc import Callable

import requests


class OllamaClient:
    def __init__(self, model: str = "qwen2.5:7b", base_url: str = "http://localhost:11434", timeout: int = 300) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def generate(self, prompt: str, *, num_predict: int = 500) -> str:
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
