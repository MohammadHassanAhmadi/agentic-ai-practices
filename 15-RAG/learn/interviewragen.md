# RAG — Interview Practice

**21 questions in 4 levels, plus a live design scenario**

> **How to use this:** answer out loud, in your own words, *before* opening the card.
> If your answer matches the **Short answer**, you're fine. If you missed the **Bonus**, that's where your depth is missing.
> The goal isn't memorising. It's being able to explain **why**.

---

## The system we're discussing

```text
PHASE 1 - INDEXING   documents -> chunks -> embed -> vector store

PHASE 2 - QUERY      question -> embed -> top-k nearest chunks
                              -> grounded prompt -> LLM -> answer + sources
```

---

## Level 1 — Fundamentals

<details markdown="1">
<summary><b>1. What is RAG, in one sentence?</b></summary>

**Short answer** — Find the relevant parts of your own data first, then give only those to the LLM to write the answer.

**Bonus** — The point is that the model no longer needs to *know* anything; it only needs to read what you put in front of it. That is what makes the knowledge updatable without retraining.

</details>

<details markdown="1">
<summary><b>2. Why not just put all the documents in the prompt?</b></summary>

**Short answer** — The context window is finite, cost grows linearly with tokens, and models reliably ignore material buried in the middle of a very long context (*lost in the middle*).

**Bonus** — Even when everything fits, accuracy drops. More irrelevant text in the prompt means more noise competing with the right answer.

</details>

<details markdown="1">
<summary><b>3. Why not fine-tune the model on your data?</b></summary>

**Short answer** — Fine-tuning is expensive and slow, has to be redone on every data change, produces no citations, and can't unlearn a deleted document.

**Bonus** — Fine-tuning teaches **style and behaviour**. RAG supplies **facts**. They solve different problems and are often used together.

</details>

<details markdown="1">
<summary><b>4. What is an embedding?</b></summary>

**Short answer** — A fixed-length list of numbers representing the meaning of a text. Texts with similar meaning get vectors that are close together, even with no words in common.

**Bonus** — It's the opposite of a hash. A hash scatters similar inputs apart; an embedding keeps them together. The output size is constant regardless of input length — one word and one paragraph both produce, say, 384 numbers.

</details>

<details markdown="1">
<summary><b>5. How do you measure how close two texts are?</b></summary>

**Short answer** — Cosine similarity: the angle between the two vectors. 1.0 means identical meaning, 0.0 means unrelated.

**Bonus** — The absolute number is not meaningful on its own — 0.6 is not universally "good". What matters is the **relative ranking** among candidates for the same question.

</details>

<details markdown="1">
<summary><b>6. What are the two phases of a RAG system?</b></summary>

**Short answer** — **Indexing** (offline): split documents into chunks, embed each, store the vectors. **Retrieval + generation** (online): embed the question, find the top-k nearest chunks, put them in the prompt, call the LLM.

**Bonus** — Same split as a database: building an index is a one-time expensive offline job; running a query is fast and happens per request.

</details>

---

## Level 2 — Design decisions

<details markdown="1">
<summary><b>7. Why split documents into chunks at all?</b></summary>

**Short answer** — Three reasons: embedding models have a token limit; a long document's vector becomes an average of everything and loses precision; and you want to send three relevant paragraphs to the LLM, not a hundred pages.

**Bonus** — The middle reason is the one people forget. A whole-document vector is semantically blurry — it retrieves badly even when the document is the right one.

</details>

<details markdown="1">
<summary><b>8. How do you choose chunk size, and what is overlap for?</b></summary>

**Short answer** — It's a trade-off. Too small and context is lost ("this" refers to what?); too large and you add noise and retrieve imprecisely. Typically a few hundred tokens with a small overlap between consecutive chunks so a sentence isn't cut in half.

**Bonus** — There is no universal size. It depends on document structure — legal contracts, chat logs and code all want different splits. Splitting on natural boundaries (headings, paragraphs) usually beats fixed-length splitting.

</details>

<details markdown="1">
<summary><b>9. What is top-k and how do you pick it?</b></summary>

**Short answer** — How many nearest chunks you pass to the LLM. Usually 3–5. Too few risks missing the answer; too many adds noise and cost.

**Bonus** — Raising k is cheap insurance *if* your prompt is well grounded, because the model can discard the extras. Without grounding, a high k actively hurts.

</details>

<details markdown="1">
<summary><b>10. What is grounding and why does it matter?</b></summary>

**Short answer** — An instruction that forces the model to answer only from the supplied context and to say "I don't know" when the answer isn't there.

**Bonus** — Without it the model fills gaps from its training data, and you get a confident answer that isn't backed by your documents — the worst possible failure mode, because it looks correct.

</details>

<details markdown="1">
<summary><b>11. How do you produce citations you can trust?</b></summary>

**Short answer** — Label each context line with its source, ask the model via structured output which sources it actually used, then validate those names against the chunks you actually retrieved.

**Bonus** — The naive version — printing every retrieved chunk's source — is wrong. Retrieved is not the same as used. Showing a user a source that doesn't contain the answer is worse than showing none, because it destroys trust. And the validation step matters: a model can invent a filename.

</details>

<details markdown="1">
<summary><b>12. What is a vector database and how does it differ from a normal one?</b></summary>

**Short answer** — A normal database answers "which row has id = 5". A vector database answers "which five vectors are nearest to this one". The index is over a vector space rather than a column.

**Bonus** — At small scale you don't need one — a list plus a loop works, which is exactly what this project does. You need one when re-embedding on every run becomes wasteful and linear scanning becomes slow. Options range from Chroma / FAISS (local) to pgvector (a Postgres extension) to Qdrant / Pinecone (production).

</details>

---

## Level 3 — Engineering

<details markdown="1">
<summary><b>13. Why isn't a similarity threshold enough to filter irrelevant results?</b></summary>

**Short answer** — Because it produces false positives and false negatives at the same time, and no value avoids both. In our test, a threshold of 0.3 let an irrelevant document through at 0.325 and dropped a correct one at 0.216.

**Bonus** — There's also no universal number: the right threshold depends on the embedding model, the domain, and the phrasing of the question, and must be measured against a real test set. The correct design is two layers — set the threshold low so you don't lose correct answers, and let the grounded LLM reject what doesn't belong. **Retrieve wide, filter narrow.**

</details>

<details markdown="1">
<summary><b>14. Can you change the embedding model later?</b></summary>

**Short answer** — Only by rebuilding the entire index. Vectors from two different models live in different spaces and are not comparable.

**Bonus** — This makes the embedding model a long-lived architectural commitment, not a config flag. It also means you must store which model produced an index, or you will one day compare incompatible vectors and get silent nonsense.

</details>

<details markdown="1">
<summary><b>15. Why does a similarity call return a matrix rather than a list?</b></summary>

**Short answer** — Because it's built to compare many questions against many documents in one operation. Rows are questions, columns are documents. With a single question you take row zero.

**Bonus** — Batching matters in practice: embedding and comparing in one vectorised call is dramatically faster than looping, which is why the API is shaped this way.

</details>

<details markdown="1">
<summary><b>16. Where do most RAG bugs come from?</b></summary>

**Short answer** — Retrieval, not generation. If the right chunk never reaches the prompt, no model can recover the answer. Retrieval quality is the ceiling on the whole system.

**Bonus** — This is why debugging must start by printing the retrieved chunks and their scores. Blaming the model — or swapping in a bigger one — is the classic wasted afternoon.

</details>

---

## Level 4 — Trap questions

<details markdown="1">
<summary><b>17. "How many customers cancelled in June?" — will RAG answer this?</b></summary>

**Short answer** — No, and it will fail *confidently*. RAG retrieves a handful of chunks; it never sees the whole dataset. Counting and aggregation are a database job.

**Bonus** — The right architecture routes the question: aggregate questions go to SQL (often via text-to-SQL), descriptive questions go to RAG. Knowing which questions your system *can't* answer is part of designing it.

</details>

<details markdown="1">
<summary><b>18. Two retrieved documents contradict each other. What happens?</b></summary>

**Short answer** — The model sees both and may pick either. Similarity says nothing about which is true or current.

**Bonus** — Mitigations: store a timestamp on each chunk and prefer the most recent; give documents a priority or authority level; and instruct the model to surface the conflict rather than silently choosing. Same problem as memory contradictions in the long-term memory project.

</details>

<details markdown="1">
<summary><b>19. Your RAG gives a wrong answer. How do you debug it?</b></summary>

**Short answer** — In order: (1) print the retrieved chunks — was the right one there at all? (2) if not, it's a retrieval problem: chunking, the embedding model, or k. (3) if it was there and the answer is still wrong, it's a prompt or grounding problem.

**Bonus** — Separating these two failure classes is the whole skill. They have completely different fixes, and reaching for a better LLM when the chunk was never retrieved is the most common mistake in the field.

</details>

<details markdown="1">
<summary><b>20. How do you evaluate a RAG system?</b></summary>

**Short answer** — Evaluate the two stages separately. Retrieval: for a set of questions with known correct chunks, measure how often the right chunk appears in the top-k. Generation: check the answer is supported by the retrieved context and that "I don't know" is returned when it should be.

**Bonus** — You need a small labelled question set before tuning anything — otherwise threshold, k and chunk size are being chosen by feel. Also test the negative cases explicitly: off-topic questions *must* return "I don't know".

</details>

<details markdown="1">
<summary><b>21. Keyword search or semantic search — which is better?</b></summary>

**Short answer** — Neither on its own. Semantic search handles paraphrasing; keyword search handles exact tokens like product codes, error numbers, and rare proper nouns, which embeddings often blur.

**Bonus** — Production systems typically run **hybrid search** — both, with the results merged and reranked. Saying "semantic is better" is the answer of someone who has only used it on prose.

</details>

---

## Design scenario

> **The problem:** Build an internal assistant over your company's documentation — a few thousand pages of Markdown across many repositories, updated daily. Answers must cite their source. Some documents are confidential and only visible to certain teams.

<details markdown="1">
<summary><b>How to walk through it — step by step</b></summary>

**1. Ingestion and chunking**

Split on structure, not fixed length — Markdown headings give natural boundaries. Keep a small overlap. Store rich metadata with every chunk: source path, heading, last-modified date, team/visibility.

```text
chunk = {
    "text":      "...",
    "source":    "repo/docs/billing.md#refunds",
    "team":      "finance",
    "updated_at": "...",
}
```

**2. Access control**

This is the part people forget. Filtering *after* retrieval is a leak waiting to happen — the confidential text has already been placed in the prompt. Filter **inside the query**, using metadata, so restricted chunks are never retrieved for an unauthorised user.

**3. Freshness**

Docs change daily, so indexing can't be a one-off script. Re-index changed files only, keyed by path plus content hash. A stale index produces confident outdated answers — one of the worst failure modes.

**4. Retrieval**

Hybrid search: semantic for paraphrased questions, keyword for error codes and identifiers. Retrieve wide (low threshold, k around 5), then let the grounded prompt narrow.

**5. Generation and citations**

Ground hard ("only from context, otherwise say you don't know"). Get `used_sources` via structured output and validate against the retrieved set before displaying links.

**6. Evaluation**

Build a labelled set of real questions from support channels. Measure retrieval hit rate separately from answer quality. Include off-topic questions that must return "I don't know".

**7. What it still won't do**

Aggregate questions ("how many services use Postgres?") need a different path. Say so explicitly rather than letting the system guess.

**Closing line** — *"In RAG, the model is rarely the bottleneck. Retrieval quality, metadata and freshness are the system."*

</details>

---

## Self-check

Without looking at this page, can you:

- [ ] Explain RAG and its two phases in one minute
- [ ] Explain an embedding using the hash comparison
- [ ] Say why a similarity threshold can't be a filter on its own
- [ ] Explain what grounding is and what breaks without it
- [ ] Describe how to produce citations you can trust, including the validation step
- [ ] Name the class of question RAG cannot answer, and what to use instead
- [ ] Debug a wrong answer by separating retrieval failure from generation failure
- [ ] Describe how you'd evaluate the two stages separately
- [ ] Design the scenario above on paper in ten minutes
