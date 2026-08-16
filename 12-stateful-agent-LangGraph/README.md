# Project 12 — Stateful Agent with LangGraph

## Goal
Rebuild the Stateful Agent concepts from Project 11 using LangGraph and understand which manual responsibilities are handled by the framework.

## What We Learned
- `StateGraph`
- `AgentState`
- `messages` + `add_messages`
- Nodes and edges
- Conditional routing
- LLM as a graph node
- `AzureChatOpenAI`
- `bind_tools()`
- `ToolNode`
- LLM ↔ Tool loop
- `thread_id`
- Checkpointers
- `InMemorySaver`
- `SqliteSaver`
- Persistence after process restart
- Basic `interrupt()` / `Command(resume=...)`

## Main Flow

```text
START
  ↓
 LLM
  ↓
tool call?
 ↙      ↘
yes      no
 ↓        ↓
TOOLS    END
 ↓
LLM
```

## Persistence

```python
config = {
    "configurable": {
        "thread_id": "project12-test"
    }
}
```

`thread_id` identifies the persistent conversation/run.

- `InMemorySaver` → state survives only while the process is alive.
- `SqliteSaver` → state can survive process restart.

## Project 11 → Project 12

| Manual Project 11 | LangGraph Project 12 |
|---|---|
| `run_id` | `thread_id` |
| `history_messages` | `messages` |
| manual history append | `add_messages` |
| manual loop | graph execution |
| manual routing | edges / conditional edges |
| manual tool execution | `ToolNode` |
| `save_state()` | checkpointer |
| `load_state()` | checkpointer |
| JSON persistence | SQLite checkpoints |
| manual resume/recovery | framework-managed checkpoint resume |

## Interrupt
`interrupt()` intentionally pauses a workflow and keeps its state so it can later continue with:

```python
Command(resume="yes")
```

Useful for:
- Human approval
- Human-in-the-loop
- Review before sensitive actions
- Waiting for external input

## Run
Install:

```bash
pip install -U langgraph langchain-openai langgraph-checkpoint-sqlite
```

Then run the project normally with your Azure OpenAI environment variables configured.

## Key Takeaway
LangGraph does not introduce magic. It standardizes the same state, routing, history, persistence, tool execution, and resume concepts that we implemented manually in Project 11.
