# Minimal RAG — built from scratch

A complete Retrieval-Augmented Generation pipeline in a single Python file, with **no RAG framework**.
The goal is to expose every moving part — embeddings, similarity, retrieval, grounding, citations — before letting a library hide them.

```text
documents -> embed -> search(top_k) -> grounded prompt -> answer + verified sources
```

---

## Quick start

```bash
pip install sentence-transformers langchain-openai pydantic python-dotenv
```

Create a `.env` file:

```env
AZURE_OPENAI_API_KEY=your-key-here
```

Run:

```bash
python rag.py
```

The embedding model (~90 MB) downloads once on first run, then works offline.

---

## Architecture

**Phase 1 — Indexing** (once, at startup)

Each document is embedded into a 384-dimensional vector.

```python
doc_vectors = embedding_model.encode([d["text"] for d in docs])
```

**Phase 2 — Query** (per question)

```python
question -> embed -> cosine similarity vs all doc vectors
         -> filter by MIN_SCORE -> sort -> take top_k
         -> build grounded prompt -> LLM -> structured answer
```

---

## Techniques used

### Semantic search with embeddings

Text is converted into a fixed-length vector that encodes meaning. Texts with similar meaning produce nearby vectors, so a question matches a document even with **no words in common** — something keyword search cannot do.

```text
"how do I cancel my subscription?"  vs  "To terminate your plan..."
keyword search -> 0 results
cosine similarity -> 0.65
```

Model: `all-MiniLM-L6-v2` (384 dims), running locally — free, offline, and unlimited for experimentation.

### Retrieve wide, filter narrow

A similarity threshold is **not** a reliable filter. In testing, a threshold of `0.3` simultaneously:

- let an irrelevant document through at `0.325` (false positive)
- dropped a correct document at `0.216` (false negative)

No single value avoids both. So the threshold is kept low (`0.1`) to remove only obvious noise, and semantic filtering is delegated to the LLM, which understands meaning rather than a statistical estimate.

### Grounding

The prompt forces the model to answer only from the supplied context:

```text
Answer the question using ONLY the context below.
If the answer is not in the context, say "I don't know".
Do not use any outside knowledge.
```

This is what prevents the model from filling gaps with its own training data. Verified: an off-topic question returns `I don't know` even when irrelevant documents are present in the context.

### Structured output

The answer is not free text. A Pydantic model forces a typed response:

```python
class GroundedAnswer(BaseModel):
    answer: str
    used_sources: list[str]
```

### Verified citations

Naively printing every retrieved chunk's source is misleading — *retrieved* is not *used*. Instead:

1. Each context line is prefixed with its source: `[billing.md] To terminate your plan...`
2. The model reports which sources it actually used, via structured output.
3. Those names are **validated** against the retrieved set — a model can invent a filename.

---

## Results

| Question | Answer | Sources |
|---|---|---|
| how do I cancel my subscription? | correct | `billing.md` |
| when will I get my money back? | correct | `refund-policy.md` |
| who do I talk to for help? | correct | `contact.md` |
| what is the weather in Toronto? | `I don't know` | *(none)* |

---

## Stack

| Layer | Choice |
|---|---|
| Embeddings | `sentence-transformers` — `all-MiniLM-L6-v2`, local |
| Vector store | none — Python list + linear scan |
| LLM | Azure OpenAI (any LangChain chat model works) |
| Validation | Pydantic |

---

## Limitations

This is a teaching implementation. It deliberately omits:

- **Real documents** — the corpus is six hardcoded strings
- **Chunking** — no splitting, no overlap; a large PDF cannot be handled
- **A vector store** — everything is re-embedded on every run
- **An ANN index** — search is linear over all vectors
- **Evaluation** — no labelled question set, so `top_k` and `MIN_SCORE` are chosen by inspection
- **Hybrid search** — exact tokens (error codes, IDs) are poorly served by embeddings alone

Note also that vectors from different embedding models are not comparable — changing the model requires rebuilding the entire index.

---

## License

MIT
