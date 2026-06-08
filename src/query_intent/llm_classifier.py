from __future__ import annotations

import json
from typing import Any

from src.query_intent.constants import DEFAULT_CLARIFICATION_ANSWER, _LLM_ALLOWED_INTENTS
from src.query_intent.types import ClassifierMethod, QueryIntent, QueryIntentResult


# ---------------------------------------------------------------------------
# Optional OpenAI LLM fallback classifier
# ---------------------------------------------------------------------------


class OpenAILLMIntentClassifier:
    """Use an OpenAI chat model to classify queries that rules cannot finalize."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-4.1-mini",
        timeout: float = 10,
        confidence_threshold: float = 0.7,
        client: Any | None = None,
    ) -> None:
        """Initialize the OpenAI client or accept an injected test client."""

        self._model = model
        self._confidence_threshold = confidence_threshold
        if client is not None:
            self._client = client
            return
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required when INTENT_CLASSIFIER_PROVIDER=openai.")
        try:
            from openai import OpenAI  # noqa: PLC0415
        except ImportError as exc:
            raise RuntimeError("The official OpenAI SDK is required. Install the `openai` package.") from exc
        self._client = OpenAI(api_key=api_key, timeout=timeout)

    def classify(self, query: str) -> QueryIntentResult:
        """Classify a query with the configured chat model and parse its JSON output."""

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Classify Korean or English user queries for a finance-term chatbot. "
                            "Return only JSON with intent, confidence, reason. "
                            "Allowed intents: simple, needs_web, clarify."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            'Examples:\n'
                            'Q: "삼성전자 주가 알려줘"\n'
                            'A: {"intent":"needs_web","confidence":0.95,"reason":"current_stock_price"}\n'
                            'Q: "안녕?"\n'
                            'A: {"intent":"simple","confidence":0.95,"reason":"greeting"}\n'
                            'Q: "이거 알려줘"\n'
                            'A: {"intent":"clarify","confidence":0.8,"reason":"ambiguous"}\n'
                            f'Query: "{query}"'
                        ),
                    },
                ],
                temperature=0,
                max_tokens=80,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content or ""
            return self._parse_response(content)
        except Exception:  # noqa: BLE001
            return QueryIntentResult(
                intent=QueryIntent.CLARIFY,
                confidence=0.0,
                reason="llm_classifier_failed",
                classifier_method=ClassifierMethod.LLM,
                fixed_answer=DEFAULT_CLARIFICATION_ANSWER,
            )

    def _parse_response(self, content: str) -> QueryIntentResult:
        """Parse and validate the LLM JSON response into a query intent result."""

        try:
            payload = json.loads(content)
            intent = QueryIntent(str(payload.get("intent", "")))
            confidence = float(payload.get("confidence", 0.0))
            reason = str(payload.get("reason", "llm_classifier"))
        except Exception:  # noqa: BLE001
            return QueryIntentResult(
                intent=QueryIntent.CLARIFY,
                confidence=0.0,
                reason="llm_classifier_failed",
                classifier_method=ClassifierMethod.LLM,
                fixed_answer=DEFAULT_CLARIFICATION_ANSWER,
            )

        if intent not in _LLM_ALLOWED_INTENTS:
            return QueryIntentResult(
                intent=QueryIntent.CLARIFY,
                confidence=0.0,
                reason="llm_classifier_failed",
                classifier_method=ClassifierMethod.LLM,
                fixed_answer=DEFAULT_CLARIFICATION_ANSWER,
            )
        if confidence < self._confidence_threshold:
            return QueryIntentResult(
                intent=QueryIntent.CLARIFY,
                confidence=confidence,
                reason="llm_classifier_low_confidence",
                classifier_method=ClassifierMethod.LLM,
                fixed_answer=DEFAULT_CLARIFICATION_ANSWER,
            )
        return QueryIntentResult(
            intent=intent,
            confidence=confidence,
            reason=reason,
            classifier_method=ClassifierMethod.LLM,
            fixed_answer=DEFAULT_CLARIFICATION_ANSWER if intent == QueryIntent.CLARIFY else None,
        )
