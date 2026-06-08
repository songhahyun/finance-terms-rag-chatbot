from __future__ import annotations

from src.query_intent.types import QueryIntent


# ---------------------------------------------------------------------------
# Fixed answers and rule patterns
# ---------------------------------------------------------------------------


DEFAULT_CLARIFICATION_ANSWER = "금융 용어 설명이 필요한지, 최신 시세/뉴스가 필요한지 조금 더 구체적으로 질문해주세요."
NEEDS_WEB_FALLBACK_ANSWER = "현재 시세, 뉴스, 환율처럼 실시간 정보가 필요한 질문입니다. 웹 조회 기능은 추후 개발 예정입니다."
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

_LLM_ALLOWED_INTENTS = {QueryIntent.SIMPLE, QueryIntent.NEEDS_WEB, QueryIntent.CLARIFY}
