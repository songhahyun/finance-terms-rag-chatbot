from __future__ import annotations

from collections.abc import Callable


class BaseGenerator:
    def generate(
        self,
        prompt: str,
        *,
        stream: bool = False,
        on_chunk: Callable[[str], None] | None = None,
        options: dict[str, float | int] | None = None,
    ) -> str:
        raise NotImplementedError
