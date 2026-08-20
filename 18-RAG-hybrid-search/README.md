# Project 17 — Hybrid search (dense + BM25)

**Builds on:** Project 16 (`ingest.py`, `ask.py`, Chroma store).
**Scope:** hybrid retrieval only. The cross-encoder reranker is Project 18.

---

## Goal

Right now retrieval is 100% dense. Test case 8 fails because the question and
the document share no vocabulary.

Add a second retriever (BM25, keyword-based) next to the existing dense one, and
merge the two result lists. You will implement **two different merge strategies**
and compare them on the same questions.

**One primary learning goal:** ranked lists from different scoring systems cannot
be combined by adding their scores. Fusion is a design decision, not arithmetic.

---

## New pieces

| Piece | What it is |
|---|---|
| `rank_bm25` | Small library, pure Python. Gives a BM25 score per document. |
| Fusion by score | Normalize both score lists to 0..1, then weighted sum. |
| Fusion by rank | RRF — throw the scores away, use only positions. |
| Comparison harness | Same questions through 4 retrievers, results side by side. |

Install: `pip install rank-bm25`

---

## Architecture

`ingest.py` does **not** change. The dense index is still built offline.

The BM25 index is different: it is small, cheap, and lives in memory. You build
it at process start from the chunks already stored in Chroma. Chroma is the
single source of truth for chunk text — do not re-read the markdown files.

```
startup:   Chroma.get()  ->  all chunk ids + texts  ->  tokenize  ->  BM25Okapi

per query: question ─┬─> dense_search(question, k=10)   -> [(id, distance), ...]
                     └─> sparse_search(question, k=10)  -> [(id, score), ...]
                                    │
                              fusion(dense, sparse)     -> [(id, fused_score), ...]
                                    │
                              top 4 ids -> texts -> grounded prompt -> LLM
```

### Files

| File | Role |
|---|---|
| `ingest.py` | unchanged |
| `retrieval.py` | **new** — everything about finding chunks |
| `ask.py` | changed in one place: call `hybrid_search` instead of `collection.query` |
| `compare.py` | **new** — runs `inputs.json` and prints the comparison table |

Putting retrieval in its own module matters here: `ask.py` should not know
whether retrieval is dense, sparse or hybrid. Same idea as an interface in C#.

---

## Steps

### Step 1 — load the corpus and build the BM25 index

`collection.get()` returns every row. Build the index once, at module load or in
an init function — **not** inside the search function. Rebuilding per query is
the classic mistake here.

### Step 2 — `sparse_search(question, k)`

`bm25.get_scores(tokens)` returns a score for **every** chunk, in corpus order.
You take it from there: pair scores with ids, sort, cut to k.

### Step 3 — `dense_search(question, k)`

You already have this. Just wrap it so it returns the same shape as
`sparse_search`: a list of `(chunk_id, number)`.

Both functions returning the same shape is what makes fusion possible. Decide the
shape before you write the fusion code.

### Step 4 — `weighted_fusion(dense, sparse, alpha)`

Normalize each list to 0..1, then `alpha * dense + (1 - alpha) * sparse`.

Problems you have to solve yourself:

- Chroma gives **distance** (lower is better). BM25 gives **score** (higher is
  better). One of them has to be flipped before anything else. Cosine distance
  in Chroma is in the range 0..2.
- A chunk found by only one retriever has no score in the other list. What value
  do you give it? Your choice — but write down why, it changes the results.
- Min-max normalization divides by `max - min`. If all scores are equal, that is
  a division by zero.

### Step 5 — `rrf_fusion(dense, sparse, k=60)`

```
score(chunk) = Σ  1 / (k + rank_in_that_list)
```

`rank` is the position in the list (1-based). Sum over the lists the chunk
appears in. That is the whole algorithm — no normalization, no scale problem.

Think about what `k=60` actually does before you accept it.

### Step 6 — `hybrid_search(question, top_k, strategy)`

One entry point. `strategy` picks the fusion function. Returns the final chunk
texts + metadata, exactly what `ask.py` expects today.

### Step 7 — `compare.py`

For each question in `inputs.json`, print the top 4 `source#chunk_index` for:
dense only, BM25 only, weighted, RRF. Mark whether the expected source is in the
top 4.

This table is the actual deliverable of the project. Without it you are guessing.

### Step 8 — run test case 8

If hybrid alone fixes it, say so. If it does not, find out **why** — is the
correct chunk missing from both lists (a retrieval problem, reranking will not
help), or is it present but ranked below 4 (a ranking problem, which is exactly
what a reranker fixes)? That answer decides what Project 18 has to do.

---

## Reference — the new library surface

```python
import re
from rank_bm25 import BM25Okapi

def tokenize(text: str) -> list[str]:
    # lowercase, keep letters and digits, drop punctuation
    return re.findall(r"[a-z0-9]+", text.lower())

# --- once, at startup -------------------------------------------------
rows = collection.get()          # dict with "ids", "documents", "metadatas"
chunk_ids = rows["ids"]          # list[str]
chunk_texts = rows["documents"]  # list[str] - same order as chunk_ids

bm25 = BM25Okapi([tokenize(t) for t in chunk_texts])

# --- per query --------------------------------------------------------
scores = bm25.get_scores(tokenize(question))
# numpy array, one float per chunk, SAME ORDER as chunk_ids.
# Not sorted. Not cut to k. Not normalized.
```

Everything after that line is implementation work: sorting, cutting to k, normalizing, fusing.

---

## Success criteria

1. `sparse_search` alone finds the chunk containing a rare exact word that dense
   search misses.
2. `dense_search` alone finds the paraphrased question that BM25 misses.
3. Both fusion strategies run on the same input and you can show where they
   disagree.
4. `ask.py` works through `hybrid_search` with no other change.
5. You can state, with the numbers in front of you, whether hybrid fixed test 8
   and why.

Passing every test is not the criterion. Being able to explain each row of the
comparison table is.

---

## Traps

- Merging by chunk **text** instead of chunk **id**. Ids are the join key.
- Building the BM25 index inside the search function.
- Tokenizing the query differently from the corpus. Both must go through the
  same `tokenize`.
- Assuming `get_scores` returns the top-k. It returns all of them, unsorted.
- Forgetting that BM25 scores are not comparable **between** queries — a score of
  8 is not "good" in absolute terms.

---

## Interview relevance

"How do you handle vocabulary mismatch in RAG?" is a standard question, and
"hybrid search" is the standard answer. What separates a real answer: knowing
*why* the scores cannot be added, knowing RRF by name and what `k` does, and
knowing that the retrieve stage is judged on recall while the rerank stage is
judged on precision.

**How production differs:** the store does hybrid natively (Azure AI Search,
Elasticsearch, Qdrant, pgvector + `tsvector`) instead of a Python BM25 index in
memory; the sparse side is an inverted index on disk with stemming, stopwords and
language analyzers; fusion weights are tuned against a labelled evaluation set,
not chosen by hand.
