# Project 14 — Long-Term Memory with LangGraph Store

## Goal

Rebuild the Project 13 long-term-memory capability using LangGraph's Store abstraction and runtime dependency injection.

## What Was Implemented

- `Context(user_id)` for per-run user identity
- `Runtime[Context]` inside graph nodes
- Namespace-based user isolation: `(user_id, "memories")`
- Store CRUD: create, read, update, delete
- Exact duplicate prevention
- Memory retrieval and prompt injection before the answer is generated
- LLM-based memory write policy using Pydantic structured output
- SQLite-backed persistence with `SqliteStore`
- Process-restart verification

## Files

```text
runtime_context_demo.py  LangGraph memory demo
memories.db              SQLite long-term-memory store
```

## Run

```bash
python runtime_context_demo.py
```

Run it twice. A durable preference should be saved on the first run and retrieved after a process restart.

## Core Flow

```text
Store → load memories → State.memories → prompt → LLM answer
                                      ↓
                         extract durable fact → save memory
```

## Current Limitations

- SQLite is suitable for local development, not a multi-instance production service.
- Retrieval loads all memories in the namespace; there is no semantic relevance search yet.
- Exact deduplication cannot detect paraphrases.
- LLM memory extraction is probabilistic and adds cost and latency.
