# RAG — Lesson 15

**Retrieval-Augmented Generation, built by hand**

> No RAG library. Six documents, a local embedding model, and one LLM call. The goal is to understand every moving part before letting a framework hide them.

---

## 1. The problem

An LLM has two built-in limits:

1. **It knows nothing about your data.** Your company docs, internal code, support tickets, contracts — none of it was in the training set.
2. **Its knowledge expires.** Every model has a knowledge cutoff.

So the question is simple: **how do we give the model our own data?**

---

## 2. Three approaches that failed

### Attempt 1 — Put everything in the prompt

Paste 500 pages of documentation into the prompt and ask the question.

**Why it fails:** the context window is finite; cost grows linearly with tokens; and *lost in the middle* — models reliably ignore material buried in the centre of a very long context.

### Attempt 2 — Fine-tune the model

Bake the knowledge into the weights.

**Why it fails:** expensive and slow; every data change means retraining; you cannot say which document an answer came from (no citations); and deleting one document means retraining from scratch.

> Fine-tuning is for teaching **style and behaviour**, not **changing facts**.

### Attempt 3 — Keyword search

Find the relevant section first, then send only that.

Close — but keyword search matches **words**, not **meaning**:

```text
user asks : "how do I cancel my subscription?"
document  : "To terminate your plan, go to Billing..."

keyword search  ->  0 results        (no shared words)
```

Same intent, different vocabulary. This is exactly the failure we hit in Project 14 when deduplicating memories: `"prefers dark roast"` vs `"likes dark roasted coffee"`.

### The fix — search by meaning

If meaning can be turned into numbers, similarity becomes arithmetic. That is what embeddings do.

---

## 3. Embeddings

An embedding turns text into a fixed-length list of numbers.

```python
embed("dark roast coffee")   # -> [0.12, -0.84, 0.31, ...]   384 numbers
embed("strong black coffee") # -> [0.14, -0.81, 0.29, ...]   very close
embed("car insurance")       # -> [-0.77, 0.05, 0.62, ...]   far away
```

**The rule:** texts with close meaning get close vectors — even with zero words in common.

### Mental model for a C# developer

|  | `GetHashCode()` | `embed()` |
|---|---|---|
| Small input change | completely different output | slightly different output |
| Output | one integer | list of floats |
| Used for | exact equality | measuring **similarity** |

A hash is designed to scatter similar inputs apart. An embedding is designed to keep them together. Exact opposites.

### Fixed size, always

```python
len(model.encode("hi"))                    # 384
len(model.encode("a very long paragraph")) # 384
```

One word or one paragraph — always the same length. The model compresses meaning into a fixed shape.

Each of those 384 numbers is a coordinate. So every text is a **point in 384-dimensional space**, and similar texts are nearby points. The axes have no human meaning; the model learned them.

| Dimensions | Model | Capacity | Cost |
|---|---|---|---|
| 384 | `all-MiniLM-L6-v2` | lower | light, local, free |
| 1536 | `text-embedding-3-small` | medium | medium |
| 3072 | `text-embedding-3-large` | higher | heavy |

> Vectors from two different models are **not comparable**. Change the embedding model and you must rebuild the whole index.

### Measuring closeness

Cosine similarity — the angle between two vectors:

```text
1.0   identical meaning
0.9   very close     "cancel subscription" vs "terminate plan"
0.5   loosely related
0.0   unrelated      "coffee" vs "car insurance"
```

You do not need the maths. Higher number = more similar.

---

## 4. What RAG actually is

> **RAG** = find the relevant parts of your data first, then give only those to the LLM to write the answer.

The model no longer needs to *know* anything. It only needs to read what you put in front of it.

Every RAG system has exactly two phases:

```text
PHASE 1 - INDEXING  (offline, once per data change)

  documents -> split into chunks -> embed each chunk -> store vectors

PHASE 2 - RETRIEVAL + GENERATION  (online, per question)

  question -> embed question -> find top-k nearest chunks
           -> build prompt (chunks + question) -> LLM -> answer + sources
```

Phase 1 is building a database index: once, offline, expensive.
Phase 2 is running a query: every time, online, fast.

---

## 5. The pipeline we built

### Index

```python
from sentence_transformers import SentenceTransformer

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

docs = [
    {"text": "To terminate your plan, open Billing and click Close Account.",
     "source": "billing.md"},
    {"text": "Refunds are processed within 14 business days of the request.",
     "source": "refund-policy.md"},
    # ...
]

doc_vectors = embedding_model.encode([d["text"] for d in docs])
```

### Retrieve

```python
MIN_SCORE = 0.1   # only filter obvious garbage

def search(question: str, top_k: int = 3):
    scores = embedding_model.similarity(embedding_model.encode(question), doc_vectors)[0]
    results = [(float(s), d) for s, d in zip(scores, docs)]
    results = [r for r in results if r[0] >= MIN_SCORE]
    results.sort(key=lambda pair: pair[0], reverse=True)
    return results[:top_k]
```

Note the `[0]`. `similarity()` returns a **matrix** — one row per question, one column per document. We asked one question, so we take row zero.

### Generate

```python
class GroundedAnswer(BaseModel):
    answer: str = Field(description="the answer, or 'I don't know' if not in the context")
    used_sources: list[str] = Field(
        default_factory=list,
        description="source names actually used to build the answer; empty list if none",
    )

answer_model = llm.with_structured_output(GroundedAnswer)

context = "\n".join(f"[{c['source']}] {c['text']}" for _, c in chunks)

prompt = f"""Answer the question using ONLY the context below.
If the answer is not in the context, say "I don't know".
Do not use any outside knowledge.
Each context line starts with its source in square brackets.
In used_sources return ONLY the sources you actually used. If none, return an empty list.

Context:
{context}

Question: {question}"""

result = answer_model.invoke(prompt)
```

That is the whole system. Everything else in production RAG — reranking, hybrid search, query rewriting — is optimisation on top of this skeleton.

---

## 6. The threshold lesson

The most valuable thing this project taught, learned by watching real numbers.

With `MIN_SCORE = 0.3`:

```text
0.325  "You can change your password..."   -> irrelevant, but PASSED   (false positive)
0.216  "Our support team is available..."  -> correct, but DROPPED     (false negative)
```

One threshold produced both errors at once. And no threshold avoids them:

| Threshold | False positives | False negatives |
|---|---|---|
| low (0.1) | many | few |
| high (0.5) | few | many |

**Retrieval is not a deterministic filter. It is a probabilistic ranking.**

There is also no universal number. The right threshold depends on the embedding model, the domain, and the phrasing of the question — it must be measured against a real test set, never guessed.

### The correct design: two layers

```text
retrieval  ->  probabilistic ranking   (fast, cheap, imprecise)
LLM        ->  semantic filter         (slow, costly, accurate)
```

Set the threshold **low** so you don't lose correct answers, and let the grounded prompt reject what doesn't belong. The pattern has a name: **retrieve wide, filter narrow**.

It works. Asked about the weather, `search` handed the model two irrelevant documents and the model still answered *"I don't know"* — something a similarity score could never do.

---

## 7. Grounding and citations

**Grounding** is the instruction that forces the model to answer only from the supplied context:

```text
If the answer is not in the context, say "I don't know".
Do not use any outside knowledge.
```

This is the same technique used in Project 5 for context trimming. It is what stops the model filling gaps with its own training data.

### The citation trap

A first attempt at citations printed **every retrieved chunk's source**:

```text
[Answer]  : To cancel your subscription, open Billing and click Close Account.
[Sources] : billing.md, account-security.md, enterprise-plan.md
```

Only `billing.md` was used. The other two were retrieved but irrelevant. A user clicking `enterprise-plan.md` finds nothing — worse than showing no citation at all, because it destroys trust.

**Fix, in three parts:**

1. Label each context line with its source so the model can see where text came from.
2. Ask for `used_sources` via structured output, not free text.
3. **Validate the returned sources against the retrieved set.** The model can invent a filename.

Point 3 is the Project 14 lesson again: *never trust an LLM's output directly.*

---

## 8. Where this design breaks

| Limitation | Why |
|---|---|
| Retrieval quality is the ceiling | If the right chunk isn't retrieved, no model can save the answer. Most RAG bugs are retrieval bugs. |
| Aggregate questions | *"How many customers cancelled in June?"* — RAG sees a few chunks, never the whole dataset. That is a SQL job. |
| Contradictions between documents | The model sees both and may pick wrong. Needs dating and priority. |
| Stale index | Document changed, index didn't — a confident, outdated answer. |
| No real documents | Six hardcoded strings, no files, no chunking. |
| No vector store | Everything is re-embedded on every run. Impossible at 1,000 documents. |
| Linear search | Every vector compared one by one. |

---

## 9. Glossary

| Term | Meaning |
|---|---|
| **Embedding** | Turning text into a list of numbers that preserves meaning |
| **Vector** | That list of numbers |
| **Chunk** | A small piece of a document |
| **Chunking** | Splitting documents into chunks |
| **Overlap** | Shared text between consecutive chunks so context isn't cut |
| **Vector store** | Database that stores vectors and finds nearest neighbours |
| **Cosine similarity** | Similarity measure between two vectors (1 = identical) |
| **Top-k** | How many nearest chunks you take |
| **Retrieval** | Finding the relevant chunks |
| **Augmentation** | Attaching those chunks to the prompt |
| **Generation** | The LLM writing the answer |
| **Semantic search** | Search by meaning (vs keyword) |
| **Hybrid search** | Keyword + semantic combined |
| **Reranking** | Re-ordering results with a more accurate model |
| **Grounding** | Forcing the model to answer only from context |
| **Citation** | Reporting which sources the answer came from |

---

*Next: real files, chunking with overlap, and a vector store so embedding happens once.*
