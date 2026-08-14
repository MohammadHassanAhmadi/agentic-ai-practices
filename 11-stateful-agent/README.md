# Project 11 — Stateful Agent

## Goal
Build a framework-free agent that can keep explicit runtime state, persist it to disk, recover after crashes, and resume a previous run safely.

## What We Built
- `AgentState`
- `run_id` per run
- JSON persistence for state and history
- `load_or_create_state()`
- History serialization
- Crash recovery for incomplete tool calls
- State/history synchronization
- Resume support
- Completed-run detection

## Core Idea
- **History** = what happened during the conversation/tool loop
- **State** = the current snapshot of the run

The agent receives the current state on every iteration and updates it after actions.

## Runtime Flow

```text
run_agent(run_id)
    ↓
load/create state
    ↓
load history
    ↓
recover incomplete history
    ↓
sync state with history
    ↓
LLM decision
    ↓
tool execution
    ↓
update state + history
    ↓
persist both
    ↓
next iteration / final answer
```

## Persistence Structure

```text
runs/
└── <run_id>/
    ├── state.json
    └── history.json
```

## Important Recovery Rule
A persisted `function_call` without its matching `function_call_output` is incomplete.

On resume:
- detect unmatched calls by `call_id`
- remove incomplete calls from history
- rebuild completed state from successful call/output pairs

## Run Lifecycle
A run can be:

- Fresh
- Interrupted and resumed
- Already completed

`state.done` prevents an already completed run from starting again.

## How to Run
Run the app normally:

```bash
python app.py
```

For resume testing, use a fixed run ID:

```python
run_id = "resume-test-1"
```

## Final Tests

### 1. Fresh Run
Delete previous persisted data and execute with a new `run_id`.

Expected:
- new state
- new history
- task completes
- `state.done == True`

### 2. Crash + Resume
Run the agent, kill the process during execution, then start again with the same `run_id`.

Expected:
- previous state/history load
- incomplete history is recovered
- completed work is preserved
- agent continues instead of restarting

### 3. Already Completed
Run again with the `run_id` of a completed task.

Expected:
- agent detects `state.done`
- LLM loop is not started again

## Intentionally Deferred
- database persistence
- atomic transactions
- history compaction/summarization
- multiple results for repeated same-name tools
- parent/trace IDs
- cancellation improvements
- framework implementations such as LangGraph

These are useful production improvements, but not required for the core Stateful Agent concept.
