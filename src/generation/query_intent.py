from __future__ import annotations

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


def normalize_term(value: str) -> str:
    """Normalize query and dictionary terms for cheap exact containment checks."""
    return _NORMALIZE_PATTERN.sub("", value).casefold()


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
        matches = self.dictionary.find_matches(query)
        token_matches = self.dictionary.find_token_matches(self._token_forms(query))
        seen = set(matches)
        for term in token_matches:
            if term not in seen:
                matches.append(term)
                seen.add(term)
        return matches

    def _token_forms(self, query: str) -> list[str]:
        try:
            return [token.form for token in self._kiwi.tokenize(query)]
        except Exception:  # noqa: BLE001
            return []

    @staticmethod
    def _has_current_info_signal(normalized_query: str) -> bool:
        has_current_word = any(normalize_term(pattern) in normalized_query for pattern in _CURRENT_INFO_PATTERNS)
        has_market_word = any(normalize_term(pattern) in normalized_query for pattern in _MARKET_INFO_PATTERNS)
        return has_market_word or (has_current_word and any(word in normalized_query for word in ("금리", "환율", "주가")))

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
