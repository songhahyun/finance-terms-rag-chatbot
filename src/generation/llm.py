from __future__ import annotations

from src.generation.ollama import OllamaGenerator


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
