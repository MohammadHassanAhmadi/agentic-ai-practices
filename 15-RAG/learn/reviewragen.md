# Project 15 — Review

**Minimal RAG, built by hand · August 2026**

---

## What was built

A complete retrieval-augmented question answering pipeline in a single file, with no RAG framework.

```text
6 documents -> embed once -> search(top_k) -> grounded prompt -> structured answer + citations
```

| Component | Choice |
|---|---|
| Embeddings | `sentence-transformers` / `all-MiniLM-L6-v2`, 384 dims, local |
| Vector store | none — a Python list and a loop |
| LLM | Azure OpenAI `gpt-5.4-nano` (Gemini used first, then switched) |
| Structured output | Pydantic `GroundedAnswer` via `with_structured_output` |
| Test set | 4 questions, including one deliberately off-topic |

**Result:** all four questions correct. Right answer, correct single source, and `I don't know` with an empty source list for the off-topic question.

---

## Decisions that were right

**Local embeddings for learning.** When Azure credit ran out, moving to a local model was the correct call — not a compromise. Retrieval is the part that needs hundreds of repetitions while learning, and a rate limit or a bill in that loop is a real obstacle. Keeping the paid model for the small number of LLM calls is the right split.

**`answer(question, context)` instead of `answer(question)`.** Retrieval was deliberately kept out of the generation function. That makes the generation step testable without an embedding model, and it is the same boundary discipline as `Runtime` vs `BaseStore` in Project 14. This was noticed and applied without prompting.

**`time.sleep` in the test loop.** Rate limits and cost were considered before they became a problem.

**Predicting the threshold outcome.** When asked what filtering would do, the answer — "put a limit on the score" — was the correct instinct, and the follow-up trap was understood immediately once the numbers were on screen.

---

## Bugs hit, and what each one taught

| Bug | Root cause | Lesson |
|---|---|---|
| Only one search result returned | Missing `[0]` — `similarity()` returns a matrix, not a list | Read what an API actually returns; shape errors fail silently, not loudly |
| Same question searched every iteration | `questions[0]` instead of `q` inside the loop | Classic loop-variable slip |
| Sorting by tuple instead of score | `sorted(..., reverse=True)` with no `key` | Tuple comparison falls through to the second element on ties — be explicit |
| Inverted router logic | `if candidate is None: return "save"` (Project 14, same pattern recurring) | Read a condition out loud before trusting it |
| Citations listed every retrieved source | Context had no source labels; model was guessing | Retrieved ≠ used |

None of these were conceptual failures. All were mechanical, and all were found by looking at output rather than by guessing.

---

## Concepts demonstrated

- **Embeddings as a similarity space** — including why they are the inverse of a hash, why the output length is fixed, and why two models' vectors are not comparable.
- **Cosine similarity as ranking, not truth** — the absolute number is meaningless; the ordering is what matters.
- **Threshold trade-off** — seen empirically: a single threshold produced a false positive (0.325, irrelevant) and a false negative (0.216, correct) in the same run.
- **Retrieve wide, filter narrow** — lowering the threshold and letting a grounded prompt do the semantic filtering.
- **Grounding** — the same technique as the context-trimming rule in Project 5, reapplied.
- **Structured output for a program decision** — `GroundedAnswer`, the same pattern as `MemoryDecision` in Project 14.
- **Never trust model output** — validating `used_sources` against the retrieved set.

---

## Weak points to watch

**1. Instructions were applied partially.** When three changes were requested — label the context with sources, tell the prompt to return only used sources, validate the output — the first version shipped with none of them, while the surrounding code was rewritten correctly. The pipeline ran, the output looked plausible, and the missing pieces were invisible without checking. *Habit to build: before running, re-read the requirement list and tick each item.*

**2. Copying without asking why.** The `runtime` vs `BaseStore` parameter difference in Project 14 was copied from elsewhere and its reason unknown until asked. Same risk here with `with_structured_output`. *The fix is cheap: when pasting an unfamiliar signature, ask one question — "why this argument and not another?"*

**3. Reading return shapes.** The `[0]` bug and the tensor-in-a-tuple bug are the same underlying habit: assuming a return type instead of printing it. In an unfamiliar library, `print(type(x))` and `print(x.shape)` cost nothing.

None of these are conceptual gaps. They are process habits, and they are the difference between code that works and code that works the first time.

---

## Where this project stops

| Missing | Why it matters |
|---|---|
| Real documents | Six hardcoded strings — no files, no formats, no messy input |
| Chunking | A 100-page PDF cannot be embedded as one vector |
| Vector store | Everything is re-embedded on every run; impossible at 1,000 documents |
| Nearest-neighbour index | Search is linear over all vectors |
| Evaluation | No labelled set, so k / threshold / chunk size are chosen by feel |
| Hybrid search | Exact tokens — error codes, product IDs — are poorly served by embeddings alone |

---

## Verdict

The core mechanics of RAG are understood, not just used. The most valuable moment in the project was not the working pipeline — it was watching one threshold create two opposite errors at once, and drawing the correct architectural conclusion from it. That is the difference between someone who has read about RAG and someone who has built it.

**Next:** real files on disk, chunking with overlap, and a vector store so embedding happens once.
