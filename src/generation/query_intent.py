from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class QueryIntent(StrEnum):
    SIMPLE = "simple"
    NEEDS_RAG = "needs_rag"
    NEEDS_WEB = "needs_web"
    CLARIFY = "clarify"


class ClassifierMethod(StrEnum):
    RULE = "rule"
    LLM = "llm"
    MERGED = "merged"


@dataclass(frozen=True)
class QueryIntentResult:
    intent: QueryIntent
    confidence: float
    reason: str
    matched_terms: list[str] = field(default_factory=list)
    classifier_method: ClassifierMethod = ClassifierMethod.RULE
    fixed_answer: str | None = None

    def routing_metadata(self) -> dict[str, object]:
        return {
            "intent": self.intent.value,
            "routing_reason": self.reason,
            "matched_terms": list(self.matched_terms),
            "classifier": {
                "method": self.classifier_method.value,
                "confidence": self.confidence,
            },
        }


_NORMALIZE_PATTERN = re.compile(r"[\s\-_./]+")
_ASCII_ALNUM_PATTERN = re.compile(r"[a-z0-9]")


def normalize_term(value: str) -> str:
    """Normalize query and dictionary terms for cheap exact containment checks."""
    return _NORMALIZE_PATTERN.sub("", value).casefold()

def _allows_short_substring_match(normalized_term: str) -> bool:
    """Return whether a normalized term can be matched as a short substring."""

    return bool(_ASCII_ALNUM_PATTERN.search(normalized_term))


@dataclass(frozen=True)
class FinanceTermDictionary:
    terms: tuple[str, ...]
    normalized_to_terms: dict[str, tuple[str, ...]]

    @classmethod
    def load(cls, path: str | Path) -> FinanceTermDictionary:
        term_order: list[str] = []
        normalized: dict[str, list[str]] = {}
        seen_terms: set[str] = set()

        for raw_line in Path(path).read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            term = line.split("\t", 1)[0].strip()
            if not term or term in seen_terms:
                continue
            seen_terms.add(term)
            term_order.append(term)
            normalized_key = normalize_term(term)
            if normalized_key:
                normalized.setdefault(normalized_key, []).append(term)

        return cls(
            terms=tuple(term_order),
            normalized_to_terms={key: tuple(value) for key, value in normalized.items()},
        )

    def find_matches(self, query: str) -> list[str]:
        normalized_query = normalize_term(query)
        if not normalized_query:
            return []

        matches: list[str] = []
        seen: set[str] = set()
        for normalized_term, terms in self.normalized_to_terms.items():
            if normalized_term not in normalized_query:
                continue
            for term in terms:
                if term not in seen:
                    seen.add(term)
                    matches.append(term)
        return matches

    def find_token_matches(self, tokens: list[str]) -> list[str]:
        matches: list[str] = []
        seen: set[str] = set()
        for token in tokens:
            normalized_token = normalize_term(token)
            if not normalized_token:
                continue
            for term in self.normalized_to_terms.get(normalized_token, ()):
                if term not in seen:
                    seen.add(term)
                    matches.append(term)
        return matches


DEFAULT_CLARIFICATION_ANSWER = "금융 용어 설명이 필요한지, 최신 시세/뉴스가 필요한지 조금 더 구체적으로 질문해주세요."
NEEDS_WEB_FALLBACK_ANSWER = "현재 시세, 뉴스, 환율처럼 실시간 정보가 필요한 질문입니다. 아직 웹 조회 기능은 연결되지 않았습니다."
GREETING_ANSWER = "안녕하세요. 경제·금융 용어 설명과 관련 질문에 답하는 챗봇입니다."
CAPABILITY_ANSWER = "경제·금융 용어의 뜻, 관련 개념, 문서 기반 설명 질문에 답할 수 있습니다."
UNSUPPORTED_DOMAIN_ANSWER = "이 챗봇은 경제·금융 용어 설명에 특화되어 있어 해당 질문에는 답하기 어렵습니다."

_CURRENT_INFO_PATTERNS = (
    "오늘",
    "어제",
    "내일",
    "최근",
    "최신",
    "현재",
    "실시간",
    "지금",
    "today",
    "yesterday",
    "tomorrow",
    "latest",
    "recent",
    "now",
    "current",
)
_MARKET_INFO_PATTERNS = (
    "주가",
    "시세",
    "환율",
    "뉴스",
    "공시",
    "현재값",
    "price",
    "stockprice",
    "stock",
    "exchangerate",
    "news",
)
_CONCEPTUAL_QUERY_PATTERNS = (
    "관계",
    "차이",
    "뜻",
    "의미",
    "개념",
    "설명",
    "무엇",
    "뭐야",
    "원리",
    "relationship",
    "difference",
    "meaning",
    "concept",
    "explain",
)
_GREETING_PATTERNS = ("안녕", "hello", "hi")
_CAPABILITY_PATTERNS = ("어떤챗봇", "무슨챗봇", "어떤질문", "답할수", "할수있어", "capability")
_UNSUPPORTED_PATTERNS = (
    "점심",
    "메뉴",
    "날씨",
    "파이썬",
    "python",
    "리스트컴프리헨션",
    "listcomprehension",
)


class RuleBasedQueryClassifier:
    def __init__(self, dictionary_path: str | Path) -> None:
        self.dictionary = FinanceTermDictionary.load(dictionary_path)
        self._kiwi = self._build_kiwi(dictionary_path)

    @staticmethod
    def _build_kiwi(dictionary_path: str | Path) -> Any:
        try:
            from kiwipiepy import Kiwi  # noqa: PLC0415
        except ImportError as exc:
            raise RuntimeError("kiwipiepy is required for rule-based query classification.") from exc

        kiwi = Kiwi()
        load_user_dictionary = getattr(kiwi, "load_user_dictionary", None)
        if callable(load_user_dictionary):
            load_user_dictionary(str(dictionary_path))
        return kiwi

    def classify(self, query: str) -> QueryIntentResult:
        normalized_query = normalize_term(query)
        if self._has_current_info_signal(normalized_query):
            matched_terms = self._match_finance_terms(query)
            return QueryIntentResult(
                intent=QueryIntent.NEEDS_WEB,
                confidence=1.0,
                reason="matched_current_information_signal",
                matched_terms=matched_terms,
                classifier_method=ClassifierMethod.RULE,
                fixed_answer=NEEDS_WEB_FALLBACK_ANSWER,
            )

        matched_terms = self._match_finance_terms(query)
        if matched_terms:
            return QueryIntentResult(
                intent=QueryIntent.NEEDS_RAG,
                confidence=1.0,
                reason="matched_finance_terms",
                matched_terms=matched_terms,
                classifier_method=ClassifierMethod.RULE,
            )

        simple_result = self._classify_simple(normalized_query)
        if simple_result is not None:
            return simple_result

        return QueryIntentResult(
            intent=QueryIntent.CLARIFY,
            confidence=1.0,
            reason="rule_no_match",
            classifier_method=ClassifierMethod.RULE,
            fixed_answer=DEFAULT_CLARIFICATION_ANSWER,
        )

    def _match_finance_terms(self, query: str) -> list[str]:
        """Return unique finance terms matched by substring or tokenizer output."""

        substring_matches = self._match_finance_terms_by_substring(query)
        token_matches = self._match_finance_terms_by_tokens(query)
        return self._merge_finance_term_matches(substring_matches, token_matches)

    def _match_finance_terms_by_substring(self, query: str) -> list[str]:
        """Find finance terms using normalized substring matching with short-term guards."""

        normalized_query = normalize_term(query)
        if not normalized_query:
            return []

        matches: list[str] = []
        seen: set[str] = set()
        for normalized_term, terms in self.dictionary.normalized_to_terms.items():
            if len(normalized_term) < 3 and not _allows_short_substring_match(normalized_term):
                continue
            if normalized_term not in normalized_query:
                continue
            for term in terms:
                if term not in seen:
                    seen.add(term)
                    matches.append(term)
        return matches

    def _match_finance_terms_by_tokens(self, query: str) -> list[str]:
        """Find finance terms by exact normalized match against Kiwi token forms."""

        return self.dictionary.find_token_matches(self._token_forms(query))

    def _merge_finance_term_matches(
        self,
        substring_matches: list[str],
        token_matches: list[str],
    ) -> list[str]:
        """Merge finance-term matches and drop shorter terms contained in longer terms."""

        matches: list[str] = []
        seen: set[str] = set()
        for term in [*substring_matches, *token_matches]:
            if term not in seen:
                seen.add(term)
                matches.append(term)

        normalized_matches = [(term, normalize_term(term)) for term in matches]
        filtered: list[str] = []
        for term, normalized_term in normalized_matches:
            if any(
                normalized_term != other_normalized
                and normalized_term in other_normalized
                and len(normalized_term) < len(other_normalized)
                for _, other_normalized in normalized_matches
            ):
                continue
            filtered.append(term)
        return filtered

    def _token_forms(self, query: str) -> list[str]:
        try:
            return [token.form for token in self._kiwi.tokenize(query)]
        except Exception:  # noqa: BLE001
            return []

    @staticmethod
    def _has_current_info_signal(normalized_query: str) -> bool:
        """Return whether the query asks for market or time-sensitive information."""

        has_current_word = any(normalize_term(pattern) in normalized_query for pattern in _CURRENT_INFO_PATTERNS)
        has_market_word = any(normalize_term(pattern) in normalized_query for pattern in _MARKET_INFO_PATTERNS)
        has_conceptual_word = any(
            normalize_term(pattern) in normalized_query for pattern in _CONCEPTUAL_QUERY_PATTERNS
        )
        return (has_market_word and not has_conceptual_word) or (
            has_current_word and any(word in normalized_query for word in ("금리", "환율", "주가"))
        )

    @staticmethod
    def _classify_simple(normalized_query: str) -> QueryIntentResult | None:
        if any(normalize_term(pattern) in normalized_query for pattern in _GREETING_PATTERNS):
            return QueryIntentResult(
                intent=QueryIntent.SIMPLE,
                confidence=1.0,
                reason="matched_greeting",
                classifier_method=ClassifierMethod.RULE,
                fixed_answer=GREETING_ANSWER,
            )
        if any(normalize_term(pattern) in normalized_query for pattern in _CAPABILITY_PATTERNS):
            return QueryIntentResult(
                intent=QueryIntent.SIMPLE,
                confidence=1.0,
                reason="matched_chatbot_capability",
                classifier_method=ClassifierMethod.RULE,
                fixed_answer=CAPABILITY_ANSWER,
            )
        if any(normalize_term(pattern) in normalized_query for pattern in _UNSUPPORTED_PATTERNS):
            return QueryIntentResult(
                intent=QueryIntent.SIMPLE,
                confidence=1.0,
                reason="unsupported_domain_fixed_answer",
                classifier_method=ClassifierMethod.RULE,
                fixed_answer=UNSUPPORTED_DOMAIN_ANSWER,
            )
        return None


_LLM_ALLOWED_INTENTS = {QueryIntent.SIMPLE, QueryIntent.NEEDS_WEB, QueryIntent.CLARIFY}


class OpenAILLMIntentClassifier:
    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-4.1-mini",
        timeout: float = 10,
        confidence_threshold: float = 0.7,
        client: Any | None = None,
    ) -> None:
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


class QueryIntentClassifier:
    def __init__(
        self,
        *,
        rule_classifier: RuleBasedQueryClassifier,
        llm_classifier: OpenAILLMIntentClassifier | None = None,
        cache_size: int = 256,
    ) -> None:
        self._rule_classifier = rule_classifier
        self._llm_classifier = llm_classifier
        self._cache_size = max(cache_size, 0)
        self._cache: dict[str, QueryIntentResult] = {}

    def classify(self, query: str) -> QueryIntentResult:
        if query in self._cache:
            return self._cache[query]
        rule_result = self._rule_classifier.classify(query)
        if self._is_rule_final(rule_result):
            return self._remember(query, rule_result)
        if self._llm_classifier is None:
            return self._remember(query, rule_result)
        return self._remember(query, self._llm_classifier.classify(query))

    def _remember(self, query: str, result: QueryIntentResult) -> QueryIntentResult:
        if self._cache_size == 0:
            return result
        if len(self._cache) >= self._cache_size:
            oldest_key = next(iter(self._cache))
            self._cache.pop(oldest_key, None)
        self._cache[query] = result
        return result

    @staticmethod
    def _is_rule_final(result: QueryIntentResult) -> bool:
        if result.intent in {QueryIntent.NEEDS_WEB, QueryIntent.NEEDS_RAG, QueryIntent.SIMPLE}:
            return True
        return result.reason != "rule_no_match"

