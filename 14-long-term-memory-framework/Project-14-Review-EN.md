# Project 14 Review — Long-Term Memory with LangGraph Store

## Core Idea

LangGraph separates the data being processed from dependencies and durable memory:

```text
State   → mutable data for one graph run
Context → static metadata for this invocation, such as user_id
Runtime → LangGraph object that gives a node access to Context and Store
Store   → long-term data shared across runs and threads
```

## Architecture

```text
graph.invoke(input, context=Context(user_id))
       ↓
load_user_memories(state, runtime)
       ↓
runtime.store.search((user_id, "memories"))
       ↓
state["memories"] → LLM prompt → answer
       ↓
extract durable memory with structured output
       ↓
runtime.store.put(...) when approved
```

## Key Concepts

- A Store item is organized by `namespace`, `key`, and JSON `value`.
- `(user_id, "memories")` is our logical isolation boundary. It is not a physical folder.
- `Runtime` is dependency injection supplied by LangGraph; nodes do not construct it.
- `put(new_key, value)` creates an item. `put(existing_key, value)` updates it.
- `get()` reads one item. `search()` reads a namespace. `delete()` removes one item.
- `InMemoryStore` is for development/testing only. `SqliteStore` survives restart.
- A user message must pass a write policy before it becomes long-term memory.
- Pydantic structured output turns the write decision into reliable fields instead of parsing free text.

## Mental Model

```text
namespace ≈ database partition / tenant boundary
key       ≈ row key / record ID
value     ≈ JSON document
```

```text
Node          ≈ framework entry point / controller
Runtime       ≈ injected execution context
Helper method ≈ application service with explicit dependencies
```

## Verified Scenarios

- Two users cannot read each other's namespace.
- Repeated exact memory is not stored twice.
- Existing memory can be updated by keeping its key.
- A memory can be deleted using both namespace and key.
- Stored memory influences the next LLM answer.
- A stable preference is saved; a normal question is rejected.
- SQLite memory remains after restart.

## Common Mistakes

- Saving every user message. This creates permanent junk and raises privacy risk.
- Using `thread_id` as the long-term-memory owner. Threads are conversations, not users.
- Giving helpers the full `Runtime` everywhere. Use it in nodes; pass focused dependencies to reusable helpers.
- Expecting `InMemoryStore` to persist after the Python process ends.
- Using a new UUID when trying to update a memory. A new key means a new item.

## Limitations and Next Step

- Current retrieval is namespace-wide, not relevant-memory retrieval.
- Exact matching does not detect semantic duplicates or conflicts.
- The next project, RAG fundamentals, will introduce embeddings and semantic retrieval.

## Keywords

LangGraph Store, `BaseStore`, `SqliteStore`, `InMemoryStore`, namespace, key-value store, `Runtime`, `Context`, `StateGraph`, dependency injection, `user_id`, long-term memory, structured output, Pydantic, write policy, prompt injection, persistence, user isolation, upsert, deduplication.

## Interview Questions and Short Answers

1. **State vs Context vs Store?**
   State changes during one run; Context is static invocation metadata; Store holds durable cross-run data.

2. **Why use `user_id` in the namespace?**
   It isolates each user's memory and prevents cross-user data leakage.

3. **Does `put()` create or update?**
   Both. It is an upsert: a new key creates; an existing key updates.

4. **Why not save every prompt?**
   Most prompts are temporary or irrelevant. Storing them pollutes retrieval and can preserve sensitive data.

5. **Why is `Runtime` useful?**
   LangGraph injects context and the active Store without globals or manual parameter plumbing at the graph boundary.

6. **Why not pass `Runtime` to every helper?**
   It couples business logic to LangGraph and makes isolated tests harder. Pass only the needed dependency, such as `BaseStore`.

7. **Why is `InMemoryStore` not long-term memory in production?**
   It lives only in the process RAM and is lost on restart.

8. **What does this project still lack?**
   Semantic retrieval, contradiction handling, memory ranking, expiry policy, and a production multi-instance database.
