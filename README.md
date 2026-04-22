# finance-terms-rag-chatbot

금융 용어 문서를 기반으로 답변하는 RAG 챗봇 프로젝트입니다.

## 1) 설치

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

환경변수는 루트의 `.env`를 사용합니다.

## 2) 백엔드 실행 (FastAPI)

```bash
uvicorn src.serving.app:app --reload --host 0.0.0.0 --port 8000
```

기본 API 엔드포인트:
- `GET /health`
- `POST /chat`

## 3) 프론트엔드 실행 (Streamlit)

```bash
streamlit run src/app/streamlit_app.py
```

기본적으로 `http://localhost:8000/chat` 백엔드와 연동합니다.

## 4) 프로젝트 디렉토리 구조

```text
finance-terms-rag-chatbot/
├─ data/
│  ├─ raw/                  # 원본 PDF
│  ├─ processed/            # 전처리 결과 (예: final_chunk.json)
│  └─ eval/                 # 평가 데이터셋 (예: golden_testset.csv)
├─ notebooks/               # 실험/분석 노트북
├─ src/
│  ├─ app/                  # Streamlit 프론트엔드
│  │  └─ streamlit_app.py
│  ├─ serving/              # FastAPI 서빙
│  │  └─ app.py
│  ├─ ingestion/            # 데이터 파싱/정제
│  ├─ embedding/            # 임베딩/벡터스토어 구축
│  ├─ retrieval/            # BM25/Dense/Hybrid 검색기
│  ├─ generation/           # 프롬프트/답변 생성 파이프라인
│  ├─ evaluation/           # 평가 파이프라인 (RAGAS 포함)
│  └─ common/               # 공통 설정/스키마/IO
├─ chroma_clova/            # Chroma DB (clova)
├─ chroma_openai/           # Chroma DB (openai)
├─ chroma_local/            # Chroma DB (local)
├─ requirements.txt
└─ README.md
```

## 5) (선택) 평가 실행

RAGAS 평가 파이프라인 실행:

```bash
python -m src.evaluation --retrieval-mode hybrid
```

## 6) API 요청/응답 예시

`POST /chat`

요청 예시:

```json
{
  "question": "가산금리란 무엇인가요?",
  "mode": "hybrid",
  "k": 5,
  "language": "ko"
}
```

응답 예시:

```json
{
  "question": "가산금리란 무엇인가요?",
  "answer": "가산금리는 기준금리에 신용위험 등을 반영해 추가로 붙는 금리입니다.",
  "retrieved_ids": ["econ_0009", "econ_0123", "econ_0311"],
  "sources": [
    {
      "chunk_id": "econ_0009",
      "source": "D:\\AI\\projects\\finance-terms-rag-chatbot\\data\\raw\\2020_경제금융용어 700선.pdf",
      "text": "가산금리: ... (문서 본문 일부)"
    },
    {
      "chunk_id": "econ_0123",
      "source": "D:\\AI\\projects\\finance-terms-rag-chatbot\\data\\raw\\2020_경제금융용어 700선.pdf",
      "text": "기준금리와 스프레드 관련 설명 ... (문서 본문 일부)"
    }
  ]
}
```
