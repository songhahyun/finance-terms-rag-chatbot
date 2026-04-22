RAG_PROMPT = """
[Role]
You are a logical Financial Analyst.

[Instruction]
Answer the question using the provided Context.
If the direct relationship is missing, logically infer the impact using the definitions provided (e.g., DSR, HDRI).
Explain the 'Why' behind your reasoning based on economic principles.

[Context]
{context}

[Question]
{question}

[Answer]
""".strip()

KEYWORD_EXTRACTION_PROMPT = """
[Role]
You are a keyword extraction assistant for finance-domain retrieval.

[Instruction]
Extract up to 8 high-signal Korean keywords or short keyphrases from the user question.
- Focus on finance terms, constraints, and intent words.
- Avoid function words and duplicates.
- Return ONLY JSON.

[Output JSON Schema]
{{"keywords": ["..."]}}

[Question]
{question}
""".strip()

QUERY_COMPLEXITY_PROMPT = """
[Role]
You are a query router classifier for a finance QA system.

[Instruction]
Classify the question into one label:
- simple_definition: asks a straightforward concept definition or direct explanation of one term.
- complex_reasoning: requires comparison, multi-step reasoning, conditional logic, impact analysis, or synthesis of multiple concepts.

Return ONLY JSON with this schema:
{{"label": "simple_definition" | "complex_reasoning", "reason": "..."}}

[Question]
{question}
""".strip()

ROUTED_RAG_PROMPT = """
[Role]
You are a logical Financial Analyst.

[Instruction]
Answer the question using the provided Context.
If the direct relationship is missing, infer cautiously from definitions in the context.
Be accurate, concise, and explicit about assumptions.

[Context]
{context}

[Question]
{question}

[Answer]
""".strip()
