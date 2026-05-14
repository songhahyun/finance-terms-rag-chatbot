from __future__ import annotations

import re


_HIRAGANA_RE = re.compile(r"[\u3040-\u309f]")
_KATAKANA_RE = re.compile(r"[\u30a0-\u30ff\u31f0-\u31ff]")
_CJK_IDEOGRAPH_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
_LONG_CJK_SEQUENCE_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]{4,}")
_CJK_BLOCK_RE = re.compile(r"(?:[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]{2,}[\s，。！？；：、]*){2,}")
_CHINESE_JAPANESE_PUNCTUATION_RE = re.compile(r"[，。！？；：「」『』《》【】、]")
_COMMON_CHINESE_PATTERN_RE = re.compile(
    r"(?:是|的|了|在|和|与|为|对|及|或|将|从|由|该|这个|如果|因为|所以|可以|不是)"
)


def _issue_result(reason: str, detected_issues: list[str]) -> dict:
    return {
        "is_valid": False,
        "reason": reason,
        "detected_issues": detected_issues,
    }


def validate_answer_language(text: str) -> dict:
    """Validate that an answer is Korean-first and free of Chinese/Japanese drift.

    The checks are intentionally conservative around CJK ideographs because Korean
    finance text may contain isolated Hanja. Long ideograph runs or repeated CJK
    blocks are treated as suspicious; a single isolated Hanja is not.
    """
    if text is None or not text.strip():
        return _issue_result("answer is empty", ["empty_answer"])

    detected_issues: list[str] = []

    if _HIRAGANA_RE.search(text):
        detected_issues.append("contains_japanese_hiragana")
    if _KATAKANA_RE.search(text):
        detected_issues.append("contains_japanese_katakana")

    long_cjk_sequences = _LONG_CJK_SEQUENCE_RE.findall(text)
    if long_cjk_sequences:
        detected_issues.append("contains_long_cjk_ideograph_sequence")

    cjk_blocks = _CJK_BLOCK_RE.findall(text)
    if len(cjk_blocks) >= 10:
        detected_issues.append("contains_repeated_cjk_ideograph_blocks")

    cjk_count = len(_CJK_IDEOGRAPH_RE.findall(text))
    has_hangul = bool(re.search(r"[\uac00-\ud7a3]", text))
    has_cj_punctuation = bool(_CHINESE_JAPANESE_PUNCTUATION_RE.search(text))
    has_common_chinese_pattern = bool(_COMMON_CHINESE_PATTERN_RE.search(text))

    if cjk_count >= 4 and has_cj_punctuation:
        detected_issues.append("contains_cjk_text_with_chinese_japanese_punctuation")
    if cjk_count >= 6 and has_common_chinese_pattern:
        detected_issues.append("contains_common_chinese_sentence_pattern")
    if cjk_count >= 4 and not has_hangul:
        detected_issues.append("contains_cjk_text_without_korean_hangul")

    if detected_issues:
        return _issue_result("answer contains likely Chinese or Japanese text", detected_issues)

    return {
        "is_valid": True,
        "reason": "answer language passed validation",
        "detected_issues": [],
    }


def needs_regeneration(text: str) -> bool:
    """Return whether an answer should be regenerated for language drift."""
    return not validate_answer_language(text)["is_valid"]
