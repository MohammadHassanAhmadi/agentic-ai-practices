# Learn AI-Agent-Engineering — Learning Roadmap

## Goal

Become a production-capable **Agentic AI / LLM Application / AI Engineer** with strong understanding of what happens underneath frameworks.

Learning rule:

> Foundation first → Framework second

For every major concept:

```text
Understand
   ↓
Implement manually
   ↓
Verify
   ↓
Learn the production framework/tool
   ↓
Compare abstractions
   ↓
Move forward
```

---

## Teaching / Execution Rules

- One concept at a time.
- Explain **why** before code.
- Keep explanations concise, practical, and mostly in Persian.
- Hassan writes the code unless stuck or explicitly asks for the full solution.
- Avoid unnecessary complexity and rabbit holes.
- Do not repeat already-mastered concepts unless the repetition adds a new capability.
- Preserve project numbering and continuity.
- `"1"` means continue to the next step.
- A question means stop progression and resolve the ambiguity first.
- At the end of every project:
  - confirm completion;
  - create a concise README;
  - create `Project-X-Review-EN.md`;
  - create `Project-X-Review-FA.md`;
  - include concepts, use cases, keywords, and interview questions.

---

# Completed Projects

## Project 9 — Evaluation Harness
- Test cases as data
- Evaluation runner
- Deterministic scorers
- LLM-as-a-judge
- Repeated runs
- Pass rates and reports
- Regression comparison

Status: ✅ Completed

## Project 10 — Evaluation Harness Polishment
- Typed evaluation models
- Rich tool-call trajectory
- ToolCall / ToolOrder scoring
- Structured LLM judge with Pydantic
- Test isolation
- Regression evaluator
- Latency measurement

Deferred:
- Token/cost tracking
- Parallel evaluation
- CI integration
- Database-backed reports

Status: ✅ Completed

## Project 11 — Stateful Agent From Scratch
- State vs history
- Agent lifecycle
- `run_id`
- State/history persistence
- Resume after restart/crash
- Serialization
- Recovery of incomplete tool calls
- Synchronizing state from history
- Fresh/interrupted/completed lifecycle

Deferred:
- Database persistence
- Atomic transactions
- History compaction
- Advanced cancellation
- Distributed persistence

Status: ✅ Completed

## Project 12 — Stateful Agent with LangGraph
- `StateGraph`
- `AgentState`
- Nodes / edges / conditional edges
- `messages` + `add_messages`
- LLM node
- `AzureChatOpenAI`
- `bind_tools()`
- `ToolNode`
- LLM ↔ Tool loop
- `thread_id`
- Checkpointers
- `InMemorySaver`
- `SqliteSaver`
- Persistence across process restart
- Basic `interrupt()`
- Basic `Command(resume=...)`

Project 11 → Project 12:
- `run_id` → `thread_id`
- history → `messages`
- manual append → `add_messages`
- while loop → graph execution
- manual routing → edges / conditional edges
- manual tool execution → `ToolNode`
- manual save/load → checkpointer
- JSON persistence → SQLite checkpoints

Deferred:
- Advanced interrupts
- Nested graphs
- Distributed checkpoints
- PostgreSQL checkpointer
- Advanced Human-in-the-Loop

Status: ✅ Completed

## Project 13 — Long-Term Memory Agent From Scratch
- Durable memory separate from history and state
- `user_id` ownership versus `run_id` / `thread_id`
- JSON persistence across process restart
- LLM extraction with Pydantic structured output
- Memory retrieval and prompt injection
- Exact deduplication
- Update and delete operations
- User isolation
- Sandbox memory tests

Status: ✅ Completed

## Project 14 — Long-Term Memory with LangGraph Store
- `Context`, `Runtime`, and Store dependency injection
- Namespace-based user isolation: `(user_id, "memories")`
- Store CRUD with `get`, `search`, `put`, and `delete`
- `BaseStore` helpers and Graph nodes using `Runtime[Context]`
- `InMemoryStore` versus persistent `SqliteStore`
- Durable SQLite memory across process restart
- Memory retrieval before the LLM answer
- Prompt injection of retrieved memories
- LLM write policy with Pydantic structured output
- Exact duplicate prevention

Status: ✅ Completed

---

# Previously Introduced / Already Familiar

## Human-in-the-Loop / Approval
Previously implemented in earlier exercises using:
- `needs_approval`
- user confirmation
- approve / reject
- continue after approval

Do not create another full beginner HITL project unless it adds a genuinely new capability.

---

# Next Project

## Project 15 — RAG Fundamentals

Main question:

How can an agent retrieve only the knowledge relevant to the current question instead of injecting every stored memory or document?

Planned concepts:
1. RAG versus long-term memory
2. Documents, chunks, and metadata
3. Retrieval before generation
4. Relevance and context limits
5. Deterministic retrieval before embeddings
6. Evaluation of retrieved context

Status: ⏳ Next

---

# Planned Direction

Likely progression:

```text
Project 13
Long-Term Memory — From Scratch
        ↓
Long-Term Memory — Framework Implementation
        ↓
RAG Fundamentals
        ↓
Vector Search / Embeddings
        ↓
PostgreSQL + pgvector
        ↓
Production RAG
        ↓
MCP
        ↓
Multi-Agent Systems
        ↓
FastAPI / Pydantic production layer
        ↓
Observability + Evaluation
        ↓
Production architecture / deployment
```

---

# Important Deferred Topics

- Advanced Human-in-the-Loop
- Complex LangGraph interrupts
- Nested/subgraphs
- Distributed durable execution
- PostgreSQL LangGraph checkpointing
- Advanced memory policies
- History summarization / compaction
- Token and cost accounting
- Parallel evaluation
- CI evaluation gates
- Redis
- Kafka
- Kubernetes

---

# Curriculum Guardrails

Before starting a new project, answer:

1. Have we already learned this concept?
2. Does this project add a genuinely new capability?
3. Is this the best next step toward becoming a production Agentic AI Engineer?
4. Should this concept be learned manually first, or are the fundamentals already mastered?
5. Can advanced complexity be safely deferred?

If a proposed project fails these checks, adjust the roadmap instead of blindly continuing.

---

# Source of Truth

This file is the canonical progress record for the learning program.

When starting a new chat or when curriculum continuity is uncertain:
1. Read this file.
2. Identify the latest completed project.
3. Identify the current project.
4. Review deferred topics.
5. Continue from the current step without restarting mastered material.

Update this file whenever:
- a project is completed;
- the current project changes;
- a major topic is deferred;
- the roadmap changes materially.
