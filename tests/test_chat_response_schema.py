from __future__ import annotations

import json

from backend.app.schemas.chat import ChatResponse


def _response_payload() -> dict[str, object]:
    return {
        "question": "가산금리란?",
        "answer": "답변",
        "retrieved_ids": ["chunk-1"],
        "sources": [
            {
                "chunk_id": "chunk-1",
                "source": "source.pdf",
                "text": "가산금리\n\n본문",
                "term": "가산금리",
                "explanation": "본문",
                "related_terms": ["금리"],
            }
        ],
        "intent": "needs_rag",
        "routing_reason": "matched_finance_terms",
        "matched_terms": ["가산금리"],
        "classifier": {"method": "rule", "confidence": 1.0},
    }


def test_chat_response_includes_routing_metadata() -> None:
    response = ChatResponse(**_response_payload())

    dumped = response.model_dump()

    assert dumped["question"] == "가산금리란?"
    assert dumped["answer"] == "답변"
    assert dumped["retrieved_ids"] == ["chunk-1"]
    assert dumped["sources"][0]["chunk_id"] == "chunk-1"
    assert dumped["sources"][0]["term"] == "가산금리"
    assert dumped["sources"][0]["explanation"] == "본문"
    assert dumped["sources"][0]["related_terms"] == ["금리"]
    assert dumped["intent"] == "needs_rag"
    assert dumped["routing_reason"] == "matched_finance_terms"
    assert dumped["matched_terms"] == ["가산금리"]
    assert dumped["classifier"] == {"method": "rule", "confidence": 1.0}


def test_stream_final_event_can_include_routing_metadata() -> None:
    final_event = {"type": "final", **_response_payload()}

    encoded = json.dumps(final_event, ensure_ascii=False)
    decoded = json.loads(encoded)

    assert decoded["type"] == "final"
    assert decoded["intent"] == "needs_rag"
    assert decoded["routing_reason"] == "matched_finance_terms"
    assert decoded["classifier"] == {"method": "rule", "confidence": 1.0}
