# Project 13 — Long-Term Memory Agent From Scratch

## Goal

Build an agent that remembers durable user information across separate runs and process restarts without using a memory framework.

## What Was Implemented

- Separate `user_id` from `run_id`
- Extract durable memories with an LLM and Pydantic structured output
- Persist memories in `memories.json`
- Load memories by user
- Inject memory into the model instructions
- Exact duplicate prevention
- Update and delete operations
- User isolation
- Sandbox tests using a temporary file
- Memory failures do not fail an otherwise successful agent run

## Files

```text
app.py          Agent loop and memory integration
memory.py       Memory extraction and JSON persistence
test_memory.py  Isolated deterministic memory tests
memories.json   Runtime long-term memory data
```

## Run

```bash
python app.py
```

Enter a stable user ID, send messages, exit, restart the application, and use the same user ID to verify recall.

## Test

```bash
python test_memory.py
```

Expected output:

```text
All sandbox memory tests passed.
```

## Current Limitations

- JSON storage is not safe for concurrent writers.
- Duplicate detection only matches normalized exact text.
- All memories for a user are injected; there is no relevance ranking.
- Automatic extraction adds memories but does not automatically resolve contradictions.
- Each user turn requires a separate LLM call for memory extraction.
- No database, embeddings, vector search, expiry policy, or atomic transaction.

