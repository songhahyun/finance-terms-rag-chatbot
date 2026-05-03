from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Callable

from kiwipiepy import Kiwi
from langchain_community.retrievers import BM25Retriever

from src.common.schema import chunks_to_documents, load_chunks


# =============================================================================
# Kiwi instances
# =============================================================================

kiwi = Kiwi()

# 사용자 사전 오염 여부와 무관하게 후보 검증용으로 쓰는 clean Kiwi
_clean_kiwi = Kiwi()

_user_dict_loaded_paths: set[str] = set()
_user_dict_loaded_files: set[str] = set()


# =============================================================================
# Constants
# =============================================================================

_ACRONYM_RE = re.compile(r"\b[A-Z]{2,}(?:[-/][A-Z0-9]{2,})*\b")
_KOR_TERM_RE = re.compile(r"[가-힣][가-힣A-Za-z0-9·\-/]{1,30}")

_FINAL_CHUNK_JSON_FILENAME = "final_chunk.json"
_DEFAULT_USER_DICT_FILENAME = "kiwi_user_dict.tsv"

_TERM_KEYS = ("용어",)
_DESC_KEYS = ("설명",)
_RELATED_KEYS = ("연관검색어",)

KEEP_POS_PREFIXES = ("NN", "SL", "SN")

# tokenizing 단계에서 제거할 조사/불용어
STOPWORDS = {
    # 조사
    "은", "는", "이", "가", "을", "를", "의",
    "에", "에서", "에게", "께", "한테",
    "으로", "로", "와", "과", "도", "만", "부터", "까지",
    "보다", "처럼", "마저", "조차",

    # 일반 불용어
    "및", "또는", "그리고", "그러나", "하지만",
    "등", "수", "것", "경우", "관련", "통해",
}

# 사용자 사전에 들어가면 안 되는 조사/활용 결합형 suffix
BAD_USER_DICT_SUFFIXES = (
    # 조사 결합
    "은", "는", "이", "가", "을", "를", "의",
    "에", "에서", "으로", "로", "와", "과", "도", "만",

    # 하다 활용
    "하게", "하고", "하는", "하여", "하지", "한다",
    "했다", "하며", "하면", "하므로", "하도록", "하였",

    # 되다 활용
    "된다", "되는", "되어", "되지", "되고", "되며", "되면", "되었",

    # 기타 잦은 활용
    "이며", "이고", "이나", "거나",
)

# 도메인 whitelist: 반드시 사용자 사전에 유지할 용어
DOMAIN_WHITELIST = {
    "회수예상가액",
    "회수의문",
    "회수",

    # 필요 시 금융 도메인 용어 추가
    "원금비보장",
    "주가연계증권",
    "파생결합증권",
    "퇴직연금",
    "개인형퇴직연금",
    "ISA",
    "ELS",
    "DLS",
}


# =============================================================================
# Utility
# =============================================================================

def _guess_pos(term: str) -> str:
    """Guess a Kiwi POS tag for a candidate dictionary term."""
    if re.fullmatch(r"[A-Z0-9][A-Z0-9\-/]{1,}", term):
        return "NNP"
    return "NNG"


def _pick(obj: dict, keys: tuple[str, ...]) -> object:
    for key in keys:
        if key in obj:
            return obj.get(key)
    return None


def _resolve_user_dict_file(chunk_json_path: str) -> Path:
    """Return the persistent TSV file path for Kiwi user dictionary."""
    chunk_path = Path(chunk_json_path)
    return chunk_path.with_name(_DEFAULT_USER_DICT_FILENAME)


def _resolve_final_chunk_json_file(chunk_json_path: str) -> Path:
    """
    Resolve final_chunk.json from either:
    - directory path
    - direct json file path
    """
    p = Path(chunk_json_path)

    if p.is_file():
        return p

    return p / _FINAL_CHUNK_JSON_FILENAME


# =============================================================================
# 1) Candidate extraction
# =============================================================================

def _extract_terms_from_text(text: str) -> set[str]:
    """Extract acronym/Korean-like term candidates from free text."""
    terms: set[str] = set()

    if not text:
        return terms

    terms.update(
        m.group(0).strip(" ,.;:()[]{}\"'")
        for m in _ACRONYM_RE.finditer(text)
    )
    terms.update(
        m.group(0).strip(" ,.;:()[]{}\"'")
        for m in _KOR_TERM_RE.finditer(text)
    )

    return {t for t in terms if len(t) >= 2}


def _extract_terms_from_row(row: dict) -> set[str]:
    """Collect candidate finance terms from one chunk row."""
    candidates: set[str] = set()

    term = str(_pick(row, _TERM_KEYS) or "").strip()
    if term:
        candidates.add(term)

    description = str(_pick(row, _DESC_KEYS) or "").strip()
    candidates.update(_extract_terms_from_text(description))

    metadata = row.get("metadata", {})
    if isinstance(metadata, dict):
        meta_related = _pick(metadata, _RELATED_KEYS)

        if isinstance(meta_related, list):
            candidates.update(
                str(x).strip()
                for x in meta_related
                if str(x).strip()
            )

        elif isinstance(meta_related, str) and meta_related.strip():
            candidates.update(
                part.strip()
                for part in re.split(r"[,/|]", meta_related)
                if part.strip()
            )

    return {c.strip() for c in candidates if len(c.strip()) >= 2}


def _extract_user_dict_candidates(rows: list[dict]) -> set[str]:
    """Extract raw user dictionary candidates from chunk rows."""
    candidates: set[str] = set()

    for row in rows:
        candidates.update(_extract_terms_from_row(row))

    return candidates


# =============================================================================
# 2) User dictionary filtering + whitelist merge
# =============================================================================

def _has_bad_user_dict_suffix(word: str) -> bool:
    """Return True if word looks like josa/eomi-attached surface form."""
    for suffix in sorted(BAD_USER_DICT_SUFFIXES, key=len, reverse=True):
        if len(word) > len(suffix) + 1 and word.endswith(suffix):
            return True

    return False


def _is_valid_user_dict_word(word: str) -> bool:
    """
    Validate whether a candidate is appropriate for Kiwi user dictionary.

    Important:
    - Use clean Kiwi, not the global kiwi that may already have user dict entries.
    - Keep only single noun/alnum-like terms.
    - Exclude josa/eomi-attached surface forms.
    """
    word = word.strip()

    if len(word) < 2:
        return False

    if word in STOPWORDS:
        return False

    if _has_bad_user_dict_suffix(word):
        return False

    analyzed = _clean_kiwi.tokenize(word)

    if len(analyzed) != 1:
        return False

    return analyzed[0].tag.startswith(KEEP_POS_PREFIXES)


def _merge_domain_whitelist(candidates: set[str]) -> set[str]:
    """Merge curated finance-domain terms after automatic filtering."""
    return set(candidates) | DOMAIN_WHITELIST


def _build_clean_user_dict_words(rows: list[dict]) -> set[str]:
    """
    Build final cleaned user dictionary words.

    Flow:
    1. Extract raw candidates from chunk JSON.
    2. Filter noisy candidates.
    3. Merge domain whitelist.
    """
    raw_candidates = _extract_user_dict_candidates(rows)

    filtered_candidates = {
        word
        for word in raw_candidates
        if _is_valid_user_dict_word(word)
    }

    return _merge_domain_whitelist(filtered_candidates)


def _build_user_dict_entries_from_json(rows: list[dict]) -> list[tuple[str, str]]:
    """Build deduplicated and cleaned (word, POS) entries from raw chunk JSON rows."""
    words = _build_clean_user_dict_words(rows)

    return sorted(
        (word, _guess_pos(word))
        for word in words
        if len(word.strip()) >= 2
    )


# =============================================================================
# 3) User dictionary IO + registration
# =============================================================================

def _write_user_dict_tsv(path: Path, entries: list[tuple[str, str]]) -> None:
    """Persist Kiwi user dictionary entries as TSV: word<TAB>tag."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="\n") as f:
        for word, tag in sorted(entries):
            f.write(f"{word}\t{tag}\n")


def _read_user_dict_tsv(path: Path) -> list[tuple[str, str]]:
    """Load Kiwi user dictionary entries from TSV file."""
    entries: list[tuple[str, str]] = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            raw = line.strip()

            if not raw or raw.startswith("#"):
                continue

            parts = raw.split("\t")

            if len(parts) < 2:
                continue

            word = parts[0].strip()
            tag = parts[1].strip() or _guess_pos(word)

            if len(word) < 2:
                continue

            entries.append((word, tag))

    return entries


def _register_user_dict_entries(entries: list[tuple[str, str]]) -> None:
    """Register (word, POS) entries into the in-memory Kiwi instance."""
    added: set[str] = set()

    for word, tag in entries:
        if word in added:
            continue

        kiwi.add_user_word(word, tag)
        added.add(word)


def _load_kiwi_user_dictionary(chunk_json_path: str) -> None:
    """Load Kiwi dictionary from TSV, or build TSV from chunk JSON if missing."""
    user_dict_file = _resolve_user_dict_file(chunk_json_path)
    path_key = str(user_dict_file.parent.resolve())

    if not user_dict_file.exists():
        chunk_json_file = _resolve_final_chunk_json_file(chunk_json_path)

        with chunk_json_file.open("r", encoding="utf-8") as f:
            rows = json.load(f)

        entries = _build_user_dict_entries_from_json(rows)
        _write_user_dict_tsv(user_dict_file, entries)

    file_key = str(user_dict_file.resolve())

    if file_key not in _user_dict_loaded_files:
        entries = _read_user_dict_tsv(user_dict_file)
        _register_user_dict_entries(entries)
        _user_dict_loaded_files.add(file_key)

    _user_dict_loaded_paths.add(path_key)


# =============================================================================
# 4) Tokenization for BM25
# =============================================================================

def tokenize_ko(text: str) -> list[str]:
    """
    Tokenize Korean text with Kiwi for BM25.

    Flow:
    1. Kiwi tokenize.
    2. Keep noun/alnum-like POS only.
    3. Remove stopwords, including josa if emitted separately.
    """
    tokens: list[str] = []

    for token in kiwi.tokenize(text):
        form = token.form.strip()
        tag = token.tag

        if not tag.startswith(KEEP_POS_PREFIXES):
            continue

        if form in STOPWORDS:
            continue

        if len(form) < 2:
            continue

        tokens.append(form)

    return tokens


# =============================================================================
# 5) Retriever builder
# =============================================================================

def build_bm25_retriever(
    chunk_json_path: str,
    *,
    k: int = 5,
    preprocess_func: Callable[[str], list[str]] = tokenize_ko,
):
    """Build a BM25 retriever and ensure Kiwi user dictionary is loaded."""
    _load_kiwi_user_dictionary(chunk_json_path)

    chunks = load_chunks(chunk_json_path)
    docs = chunks_to_documents(chunks)

    retriever = BM25Retriever.from_documents(
        docs,
        k=k,
        preprocess_func=preprocess_func,
    )

    return retriever