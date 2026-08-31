from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

from src.generation.query_intent import (
    CAPABILITY_ANSWER,
    DEFAULT_CLARIFICATION_ANSWER,
    GREETING_ANSWER,
    NEEDS_WEB_FALLBACK_ANSWER,
    UNSUPPORTED_DOMAIN_ANSWER,
    QueryIntentResult,
    RuleBasedQueryClassifier,
)


DEFAULT_TESTSET_PATH = Path("data/eval/testset/classify_query_intent_v1.csv")
DEFAULT_INTENT_DICTIONARY_PATH = Path("data/processed/finance_intent_terms.json")
DEFAULT_KIWI_DICTIONARY_PATH = Path("data/processed/kiwi_user_dict.tsv")
DEFAULT_OUTPUT_DIR = Path("data/eval/outputs/query_intent")
OUTPUT_STEM = "query_intent_eval_v1"

_FIXED_ANSWER_KEYS = {
    DEFAULT_CLARIFICATION_ANSWER: "DEFAULT_CLARIFICATION_ANSWER",
    NEEDS_WEB_FALLBACK_ANSWER: "NEEDS_WEB_FALLBACK_ANSWER",
    GREETING_ANSWER: "GREETING_ANSWER",
    CAPABILITY_ANSWER: "CAPABILITY_ANSWER",
    UNSUPPORTED_DOMAIN_ANSWER: "UNSUPPORTED_DOMAIN_ANSWER",
}


@dataclass(frozen=True)
class TermMetrics:
    """Set-based matched-term metrics for one evaluated row."""

    exact_ok: bool
    precision: float
    recall: float


@dataclass(frozen=True)
class EvaluationOutputs:
    """Paths written by a query intent evaluation run."""

    full_csv: Path
    errors_csv: Path
    summary_json: Path


def _parse_expected_terms(raw_value: str) -> list[str]:
    """Parse the expected matched-term JSON list from the testset."""

    value = (raw_value or "").strip()
    if not value:
        return []
    parsed = json.loads(value)
    if not isinstance(parsed, list):
        raise ValueError(f"expected_matched_terms must be a JSON list: {raw_value}")
    return [str(term) for term in parsed]


def _parse_acceptable_intents(raw_value: str, expected_intent: str) -> set[str]:
    """Parse pipe-delimited acceptable intents, defaulting to the strict label."""

    intents = {item.strip() for item in (raw_value or "").split("|") if item.strip()}
    return intents or {expected_intent}


def _term_metrics(expected_terms: list[str], predicted_terms: list[str]) -> TermMetrics:
    """Compute exact, precision, and recall metrics for matched terms."""

    expected = set(expected_terms)
    predicted = set(predicted_terms)
    if not expected and not predicted:
        return TermMetrics(exact_ok=True, precision=1.0, recall=1.0)
    if not expected or not predicted:
        return TermMetrics(exact_ok=False, precision=0.0, recall=0.0)

    intersection_count = len(expected & predicted)
    return TermMetrics(
        exact_ok=expected == predicted,
        precision=intersection_count / len(predicted),
        recall=intersection_count / len(expected),
    )


def _fixed_answer_key(result: QueryIntentResult) -> str:
    """Return the symbolic fixed-answer constant name for a classifier result."""

    if result.fixed_answer is None:
        return ""
    return _FIXED_ANSWER_KEYS.get(result.fixed_answer, "UNKNOWN_FIXED_ANSWER")


def _evaluate_row(row: dict[str, str], classifier: RuleBasedQueryClassifier) -> dict[str, Any]:
    """Classify one testset row and attach row-level evaluation fields."""

    expected_intent = row["expected_intent"].strip()
    acceptable_intents = _parse_acceptable_intents(row.get("acceptable_intents", ""), expected_intent)
    expected_terms = _parse_expected_terms(row.get("expected_matched_terms", ""))
    result = classifier.classify(row["query"])
    predicted_intent = result.intent.value
    term_metrics = _term_metrics(expected_terms, result.matched_terms)
    predicted_fixed_answer_key = _fixed_answer_key(result)
    expected_fixed_answer_key = (row.get("expected_fixed_answer_key") or "").strip()

    return {
        **row,
        "predicted_intent": predicted_intent,
        "predicted_confidence": result.confidence,
        "predicted_reason": result.reason,
        "predicted_matched_terms": json.dumps(result.matched_terms, ensure_ascii=False),
        "predicted_fixed_answer_key": predicted_fixed_answer_key,
        "strict_intent_ok": predicted_intent == expected_intent,
        "acceptable_intent_ok": predicted_intent in acceptable_intents,
        "term_exact_ok": term_metrics.exact_ok,
        "term_precision": term_metrics.precision,
        "term_recall": term_metrics.recall,
        "fixed_answer_key_ok": predicted_fixed_answer_key == expected_fixed_answer_key,
    }


def _accuracy(rows: list[dict[str, Any]], field: str) -> float:
    """Compute the mean boolean value for a row field."""

    if not rows:
        return 0.0
    return mean(1.0 if row[field] else 0.0 for row in rows)


def _category_metrics(rows: list[dict[str, Any]]) -> dict[str, dict[str, float | int]]:
    """Aggregate strict, acceptable, and term metrics by testset category."""

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("category", ""))].append(row)

    return {
        category: {
            "count": len(category_rows),
            "strict_intent_accuracy": _accuracy(category_rows, "strict_intent_ok"),
            "acceptable_intent_accuracy": _accuracy(category_rows, "acceptable_intent_ok"),
            "term_exact_match_rate": _accuracy(category_rows, "term_exact_ok"),
            "average_term_precision": mean(float(row["term_precision"]) for row in category_rows),
            "average_term_recall": mean(float(row["term_recall"]) for row in category_rows),
        }
        for category, category_rows in sorted(grouped.items())
    }


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Build summary metrics for the evaluated rows."""

    confusion = Counter(f"{row['expected_intent']}->{row['predicted_intent']}" for row in rows)
    return {
        "total_rows": len(rows),
        "strict_intent_accuracy": _accuracy(rows, "strict_intent_ok"),
        "acceptable_intent_accuracy": _accuracy(rows, "acceptable_intent_ok"),
        "term_exact_match_rate": _accuracy(rows, "term_exact_ok"),
        "average_term_precision": mean(float(row["term_precision"]) for row in rows) if rows else 0.0,
        "average_term_recall": mean(float(row["term_recall"]) for row in rows) if rows else 0.0,
        "category_metrics": _category_metrics(rows),
        "confusion_counts": dict(sorted(confusion.items())),
    }


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    """Write evaluation rows to a UTF-8 CSV file."""

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def run_evaluation(
    *,
    testset_path: str | Path = DEFAULT_TESTSET_PATH,
    intent_dictionary_path: str | Path = DEFAULT_INTENT_DICTIONARY_PATH,
    kiwi_dictionary_path: str | Path = DEFAULT_KIWI_DICTIONARY_PATH,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    dictionary_path: str | Path | None = None,
) -> EvaluationOutputs:
    """Run rule-only query intent evaluation and save full, error, and summary outputs."""

    if dictionary_path is not None:
        intent_dictionary_path = dictionary_path
        kiwi_dictionary_path = dictionary_path

    classifier = RuleBasedQueryClassifier(
        intent_dictionary_path=intent_dictionary_path,
        kiwi_dictionary_path=kiwi_dictionary_path,
    )
    with Path(testset_path).open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        rows = [_evaluate_row(row, classifier) for row in reader]

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%y%m%d_%H%M")
    full_csv = output_path / f"{OUTPUT_STEM}_{timestamp}.csv"
    errors_csv = output_path / f"{OUTPUT_STEM}_{timestamp}_errors.csv"
    summary_json = output_path / f"{OUTPUT_STEM}_{timestamp}_summary.json"

    fieldnames = list(rows[0].keys()) if rows else list(csv.DictReader([]).fieldnames or [])
    error_rows = [
        row
        for row in rows
        if not row["strict_intent_ok"] or not row["acceptable_intent_ok"] or not row["term_exact_ok"]
    ]

    _write_csv(full_csv, rows, fieldnames)
    _write_csv(errors_csv, error_rows, fieldnames)
    summary = _summary(rows)
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return EvaluationOutputs(full_csv=full_csv, errors_csv=errors_csv, summary_json=summary_json)


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser for query intent evaluation."""

    parser = argparse.ArgumentParser(description="Evaluate the rule-based query intent classifier")
    parser.add_argument("--testset", default=str(DEFAULT_TESTSET_PATH))
    parser.add_argument("--intent-dictionary", default=str(DEFAULT_INTENT_DICTIONARY_PATH))
    parser.add_argument("--kiwi-dictionary", default=str(DEFAULT_KIWI_DICTIONARY_PATH))
    parser.add_argument("--dictionary", default=None, help="Legacy option that uses one dictionary for both paths")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser


def main() -> None:
    """Parse CLI arguments, run evaluation, and print written output paths."""

    args = build_parser().parse_args()
    outputs = run_evaluation(
        testset_path=args.testset,
        intent_dictionary_path=args.intent_dictionary,
        kiwi_dictionary_path=args.kiwi_dictionary,
        dictionary_path=args.dictionary,
        output_dir=args.output_dir,
    )
    print(f"full csv: {outputs.full_csv}")
    print(f"errors csv: {outputs.errors_csv}")
    print(f"summary json: {outputs.summary_json}")


if __name__ == "__main__":
    main()
