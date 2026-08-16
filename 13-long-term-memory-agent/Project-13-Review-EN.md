# Project 13 Review — Long-Term Memory Agent From Scratch

## Core Idea

Long-term memory is durable knowledge that survives separate runs, threads, and process restarts. It is not the same as conversation history or workflow state.

```text
History  → events and messages inside a conversation
State    → current workflow snapshot
Memory   → durable user knowledge across runs
RAG      → retrieval of relevant knowledge from external sources
```

## Architecture

```text
user input
   ↓
load memories by user_id
   ↓
inject memory into model instructions
   ↓
run agent and produce final answer
   ↓
extract durable facts
   ↓
save them for future runs
```

## New Concepts

- `user_id` owns long-term memory.
- `run_id` owns state and history for one execution.
- Memory should be explicit, useful, durable, and safe to store.
- Temporary facts, questions, secrets, and uncertain assumptions should not be stored.
- Pydantic structured output gives the extractor a reliable `list[str]` contract.
- Dependency injection prevents a circular import between `app.py` and `memory.py`.
- A memory subsystem should fail independently from the main agent response.

## Operations

- **Write:** create an ID, owner, content, and timestamp.
- **Retrieve:** filter memories by `user_id`.
- **Inject:** format memories as background context, not fake history.
- **Deduplicate:** normalize text and reject exact duplicates.
- **Update:** change content while keeping the same memory ID.
- **Forget:** delete by both `user_id` and memory ID.

## Verified Scenarios

- Recall after a new run
- Recall after process restart
- No memory leakage between users
- Duplicate prevention
- Update without increasing record count
- Delete and repeated-delete behavior
- Sandbox test does not modify the real memory file

## Important Limitations

- Exact matching does not detect semantic duplicates.
- Conflicting facts are not resolved automatically.
- Injecting every memory will eventually waste context tokens.
- JSON read-modify-write can lose updates under concurrency.
- LLM-based extraction adds latency and cost.

## Keywords

Long-term memory, episodic memory, semantic memory, user profile, persistence, `user_id`, `run_id`, memory extraction, memory retrieval, context injection, structured output, Pydantic, deduplication, forgetting, user isolation, race condition, lost update.

## Interview Questions

1. What is the difference between history, state, and long-term memory?
2. Why should long-term memory be keyed by `user_id` rather than `thread_id`?
3. What information should not be stored as memory?
4. Why should memories be injected as background instructions instead of fake user messages?
5. How do exact and semantic deduplication differ?
6. How would you handle a user changing an earlier preference?
7. Why is a JSON file unsafe for concurrent writes?
8. How would you prevent memory leakage between users?
9. Why should a memory extraction failure not fail the main agent response?
10. When would you use vector search for long-term memory?

