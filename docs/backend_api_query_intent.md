# Backend API Query Intent Metadata

`POST /api/chat` responses include routing metadata in addition to the existing `question`, `answer`, `retrieved_ids`, and `sources` fields.

```json
{
  "question": "가산금리란 무엇인가요?",
  "answer": "가산금리는 기준금리에 신용위험 등을 반영해 추가로 붙는 금리입니다.",
  "retrieved_ids": ["econ_0009"],
  "sources": [
    {
      "chunk_id": "econ_0009",
      "source": "한국은행 2020_경제금융용어 700선.pdf",
      "text": "가산금리: ..."
    }
  ],
  "intent": "needs_rag",
  "routing_reason": "matched_finance_terms",
  "matched_terms": ["가산금리"],
  "classifier": {
    "method": "rule",
    "confidence": 1.0
  }
}
```

`POST /api/chat/stream` final NDJSON events include the same metadata.

```json
{
  "type": "final",
  "question": "기준금리 오늘 얼마야?",
  "answer": "현재 시세, 뉴스, 환율처럼 실시간 정보가 필요한 질문입니다. 아직 웹 조회 기능은 연결되지 않았습니다.",
  "retrieved_ids": [],
  "sources": [],
  "intent": "needs_web",
  "routing_reason": "matched_current_information_signal",
  "matched_terms": ["기준금리"],
  "classifier": {
    "method": "rule",
    "confidence": 1.0
  }
}
```

`GET /api/monitor/recent` trace metadata includes classifier details under `metadata`, and `stages` includes `stage_0_intent_classification`.
