# Project 16 — Real files + chunking + vector store

## Primary learning goal

Move RAG from "a hardcoded Python list" to a real pipeline:
**files on disk → chunks → embeddings → a persistent vector store → retrieval**.

One goal, one new idea per part. Everything else you already did in Project 15.

## What changes from Project 15

| Project 15 | Project 16 |
|---|---|
| 4 hardcoded doc strings | 4 real `.md` files in `docs/` |
| whole doc = 1 vector | doc split into overlapping chunks |
| vectors in a Python list | vectors in Chroma, persisted on disk |
| embed on every run | embed once (ingest), query many times |
| manual cosine loop | `collection.query(...)` |

## Expected behaviour

Two scripts.

**`ingest.py`** — run it when the documents change.

1. Read every `.md` file in `docs/`.
2. Split each file's text into chunks.
3. Embed all chunks with the local sentence-transformers model.
4. Store them in a Chroma collection that persists to `./chroma_db/`.
5. Print how many files, how many chunks, and the final collection count.

Running it twice must **not** double the data. Decide how you handle that
(delete and rebuild, or stable ids) and say why in a comment.

**`ask.py`** — run it to ask questions.

1. Load the existing collection from disk. It must **not** re-read `docs/`
   and must **not** re-embed anything.
2. Embed the question, query the collection for the top-k chunks.
3. Build a grounded prompt from those chunks (same as Project 15).
4. Return a structured answer + the source files actually used.
5. Off-topic question → "I don't know" and an empty source list.

## Requirements

- `CHUNK_SIZE` and `CHUNK_OVERLAP` are constants at the top, easy to change.
- Every chunk carries metadata: at minimum `source` (the file name) and
  `chunk_index`.
- Citations point at the **file**, not at the raw chunk text.
- `ask.py` must work in a fresh process with `docs/` renamed away. That is the
  proof that the store is really persistent.

## What you must write yourself

- `load_documents()` — read the folder, return file name + text.
- `chunk_text(text, chunk_size, overlap)` — the splitting logic.
- The ingest loop, the id scheme, the re-run behaviour.
- Turning Chroma's query result into your context string.
- The grounded prompt + structured output (you already did this in Project 15).

## What is given to you

Only the unfamiliar API surface, in the skeleton files:

- how to create a persistent Chroma client and a collection
- the exact shape of `collection.add(...)` and `collection.query(...)`
- what the query result dict looks like

## Setup

```bash
pip install chromadb sentence-transformers
```

Embeddings: local `all-MiniLM-L6-v2` (free, 384 dims), same as Project 15.
LLM: your Azure `gpt-5.4-nano`.

## Questions to answer for yourself (before you code)

1. If a chunk is too small, what goes wrong? If it is too large?
2. Why does overlap exist at all? What breaks without it?
3. Splitting on characters vs. words vs. paragraphs — what does each get wrong?
4. Why is `hnsw:space` set to `cosine` and not the default?
5. `ingest.py` and `ask.py` are separate processes. What is the only thing
   they share, and what happens if they disagree about the embedding model?

## Test cases

See `inputs.json`. Each case has the question, the expected source file, and
what the answer must contain.

## Result — CLOSED, 7/8 passing

Test 8 (`How much vacation do I get after a production incident?`) returns
"I don't know" and no sources.

**This is a known limitation, not a bug.** The document says *"additional time
off in lieu if they are paged outside working hours"*. The question says
*"vacation"* and *"production incident"*. No shared vocabulary, and the vectors
are not close enough — the right chunk was not retrieved even at `TOP_K = 6`.

Nothing in this project's toolbox fixes it: not chunk size, not chunk
boundaries, not the prompt, not top_k. The real fixes are hybrid search
(BM25 + vector), a cross-encoder reranker, or LLM query rewriting — all of
which belong to the next project.

## For later

1. **PDF ingestion** (small) — only `load_documents` changes. New problems:
   columns, tables, repeated headers/footers, scanned PDFs needing OCR.
2. **Incremental ingest, strategy C** (small) — `file_hash` is already stored in
   metadata. Re-embed only changed files; delete chunks of removed files.
3. **LangGraph ingest** (medium) — only worth it for parallel `Send` fan-out,
   per-file retry, or resume via checkpointer. On a straight line it is pure
   overhead.
4. **Hybrid search + reranking** (large) — Project 17. Fixes test 8.
5. **Token-based chunking** (small) — needed for Persian text or code, where the
   characters-per-token ratio is completely different.

## Where this shows up in real work

This is the actual shape of every production RAG system: an offline indexing job
and an online query path, talking through a vector store. Interviewers ask about
chunk size trade-offs, re-indexing strategy, and metadata filtering far more
often than they ask about embeddings themselves.

**How production differs:** re-indexing is incremental (only changed files, by
content hash), the store is a managed service (pgvector, Pinecone, Azure AI
Search), chunking is structure-aware (headings, tables, code blocks), and there
is a reranker between retrieval and the LLM.
