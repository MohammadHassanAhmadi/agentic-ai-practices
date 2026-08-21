# Project 17 — RAG on pgvector (PostgreSQL)

Project 16 rebuilt on a real database. Same pipeline, different store, and
this time the storage layer is not hidden behind a library.

## Primary learning goal

**A vector store is a normal SQL table with one extra column type.**

By the end you should be able to open `psql`, type a query by hand, and see
your own chunks come back ranked by distance — no Python involved.

Everything else (chunking, embeddings, grounded prompt, citations) you already
did in Project 16. Reuse it.

## What changes from Project 16

| Project 16 | Project 17 |
|---|---|
| Chroma, a file in `chroma_db/` | PostgreSQL in Docker, `vector` extension |
| `collection.add(...)` | `INSERT INTO chunks (...)` |
| `collection.query(...)` | `SELECT ... ORDER BY embedding <=> %s LIMIT %s` |
| `configuration={"hnsw": {"space": "cosine"}}` | operator `<=>` + opclass `vector_cosine_ops` |
| metadata dict, `where=` filter | ordinary columns, ordinary `WHERE` |
| index built for you, invisible | you create it yourself, and prove it is used |
| hand-written `chunk_text` + `find_boundary` | `RecursiveCharacterTextSplitter` |
| `.md` only | `.md` **and** `.pdf` |

## The five new ideas

1. **`CREATE EXTENSION vector`** — pgvector is not a separate database. It is
   an extension that adds a column type and a few operators to Postgres.
2. **`vector(384)`** — the dimension is fixed in the schema. The embedding
   model is now part of your DDL. Change the model, change the table.
3. **Distance operators** — `<=>` cosine, `<->` L2, `<#>` negative inner
   product. There is no `query()` function; nearest-neighbour search is just
   `ORDER BY <operator> LIMIT k`.
4. **The index must match the operator** — `vector_cosine_ops` goes with
   `<=>`. Mismatch them and the query still returns correct rows, just slowly,
   with no warning.
5. **Approximate search** — HNSW trades recall for speed. It can miss a
   correct neighbour. Chroma made the same trade; you just never saw it.

## Expected behaviour

Two scripts, same split as Project 16.

**`ingest.py`** — offline, run when documents change.

1. Read every `.md` **and** `.pdf` in `docs/`.
2. Split with `RecursiveCharacterTextSplitter`.
3. Embed with the local `all-MiniLM-L6-v2` model (384 dims).
4. Write chunks + vectors into the `chunks` table.
5. Print files, chunks, and the final `SELECT count(*)`.

Running it twice must not double the data.

**`ask.py`** — online, run per question.

1. Connect to the same database. Do not read `docs/`, do not re-embed anything
   except the question.
2. Embed the question, run the nearest-neighbour query, take top-k.
3. Build the grounded prompt, get the structured answer + `used_sources`.
4. Off-topic question → "I don't know" and an empty source list.

## Setup

```bash
docker compose up -d
pip install "psycopg[binary]" pgvector langchain-text-splitters pypdf
```

Already installed from Project 16: `sentence-transformers`, `langchain-openai`,
`pydantic`, `python-dotenv`.

Connection string (add to `.env`):

```
DATABASE_URL=postgresql://rag:ragpass@localhost:5433/ragdb
```

Check the container is alive and the extension installs:

```bash
docker exec -it rag-postgres psql -U rag -d ragdb -c "CREATE EXTENSION IF NOT EXISTS vector;"
docker exec -it rag-postgres psql -U rag -d ragdb -c "SELECT extversion FROM pg_extension WHERE extname='vector';"
```

## Order of work

Do not write both scripts and then debug. One step, one proof.

| # | Step | Proof it works |
|---|---|---|
| 1 | Docker up, extension installed | `SELECT extversion ...` prints a version |
| 2 | Schema created | `\d chunks` in psql shows a `vector(384)` column |
| 3 | Insert **one** hand-made row | `SELECT count(*)` → 1 |
| 4 | Nearest-neighbour query by hand in psql | rows come back with a distance column |
| 5 | `ingest.py` — full `.md` pipeline | count matches Project 16's 19 chunks |
| 6 | `ask.py` — retrieval + grounded answer | 7 of 8 test cases pass, same as Project 16 |
| 7 | Create the HNSW index | `EXPLAIN ANALYZE` changes from Seq Scan to Index Scan |
| 8 | `load_pdf()` | a PDF question answers with the PDF as its source |
| 9 | Switch ingest from rebuild to incremental | second run re-embeds only the file you edited |

Step 4 is the important one. Do it in psql, not in Python.

## Ingest strategy: rebuild first, incremental last

Start with **full rebuild** (`TRUNCATE` + re-insert everything) so the pipeline
works end to end and your attention stays on pgvector. Then convert it to
**incremental** in step 9. Incremental is the real answer, for two reasons.

**Cost.** Embedding is the expensive step. If one file out of ten changed,
re-embedding the other nine is pure waste. `file_hash` is already in your table
for exactly this.

**Downtime.** This one is new — Chroma hid it from you:

```sql
TRUNCATE chunks;   -- from here the table is empty
INSERT ...         -- until here, every query returns nothing
```

Any question asked in that window gets "I don't know" and no error. The fix is
not to avoid rebuilding, it is to make the change atomic:

```sql
BEGIN;
  DELETE FROM chunks WHERE source = %s;   -- only this file's chunks
  INSERT INTO chunks (...) VALUES (...);  -- its new version
COMMIT;                                    -- readers see old or new, never half
```

A reader either sees the old version or the new one. Never a partial table.
This is the concrete thing a real database gives you that a file-backed vector
store does not, and it is worth being able to explain in an interview.

## What you must write yourself

- The `chunks` table DDL — decide the columns and the uniqueness rule.
- `load_documents()` — now dispatching on file extension.
- The ingest loop, and both re-run strategies: rebuild first, then delete-by-source.
- The nearest-neighbour SQL and turning result rows into your context string.
- The index creation and the `EXPLAIN ANALYZE` comparison.
- `load_pdf()` at the end.

## What is given to you

Only the unfamiliar API surface:

- `docker-compose.yml`
- how to connect with `psycopg` and register the vector type
- the exact SQL shape of an insert and of a nearest-neighbour query
- how `RecursiveCharacterTextSplitter` is constructed

## Questions to answer for yourself

1. `vector(384)` is in the schema. What breaks if you swap the embedding model
   for a 768-dim one and forget the table?
2. Chroma returned cosine *distance*. `<=>` returns cosine distance too, in the
   range 0–2. Where does 2 come from, and what would a distance of exactly 1
   mean?
3. You create an HNSW index with `vector_l2_ops` but query with `<=>`. What
   happens — an error, wrong results, or slow results?
4. Chunks and vectors are in the same table. When would you split them into two
   tables?
5. In Chroma, metadata filtering used a `where=` dict. Here it is a `WHERE`
   clause. Which one is more likely to be fast, and why does that depend on the
   index?
6. Full rebuild inside one transaction is safe for readers. What is it still
   bad at, and at roughly what corpus size does that start to hurt?
7. Test 8 failed in Project 16 because of vocabulary mismatch. Does moving to
   pgvector fix it? Why or why not?

## Test cases

See `inputs.json`. Cases 1–8 are the same as Project 16 — the answers must not
change just because the store changed. That is the point: **same results, new
storage layer.** Cases 9–10 are new and cover the PDF path.

## Where this shows up in real work

pgvector is the default answer for RAG at small and medium scale, because most
teams already run Postgres. One database, one backup, one set of credentials,
transactions across your business data and your vectors. Interviewers ask why
you would pick it over a dedicated vector database — the honest answer is
operational simplicity up to a few million vectors, and that a dedicated store
wins past that.

**How production differs:** connection pooling instead of one connection per
script; migrations managed by a tool, not a `CREATE TABLE IF NOT EXISTS`; the
embedding model name stored in a column so a model change is detectable;
`ivfflat`/`hnsw` parameters tuned against measured recall, not defaults.

## Next

- **Project 18** — hybrid search: PostgreSQL full-text search (`tsvector`,
  `ts_rank_cd`) or `rank_bm25` alongside the vector query, fused with weighted
  sum and with RRF. This is where test 8 finally passes.
- **Project 19** — cross-encoder reranker.
