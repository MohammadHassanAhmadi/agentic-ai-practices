# Project 11 Review — Stateful Agent

## Main Concepts

### Agent State
An explicit snapshot of the current run.

Example fields:

```python
@dataclass
class AgentState:
    current_step: str = ""
    completed_steps: list[str] = field(default_factory=list)
    data: dict = field(default_factory=dict)
    error: str | None = None
    done: bool = False
```

### History vs State

**History**
- records what happened
- user messages
- model outputs
- tool calls
- tool outputs

**State**
- represents the current situation
- completed work
- useful results
- current error
- completion status

Short rule:

```text
History = events
State   = current snapshot
```

## Giving State to the LLM
The current state is converted into context and included in each model iteration.

Do not keep appending old state snapshots to history.

Use the latest state snapshot instead.

## State Persistence
Each run has a stable `run_id`.

State is persisted as JSON so the same run can be restored later.

Key functions:

```text
save_state()
load_or_create_state()
```

## History Persistence
History is also stored separately.

```text
save_history()
load_history()
```

Keeping state and history separate is useful because they have different purposes and may evolve differently.

## Serialization
Responses API output items are not always plain JSON dictionaries.

Before saving history, convert SDK/Pydantic-like objects into serializable dictionaries, for example with:

```python
item.model_dump()
```

## Crash Consistency
A crash can happen after a model emits a tool call but before the tool result is appended.

Bad persisted history:

```text
function_call
(no matching function_call_output)
```

This causes resume requests to fail.

## History Recovery
On resume:
1. collect completed `function_call_output.call_id` values
2. find unmatched `function_call` items
3. remove incomplete calls
4. persist the recovered history

## State Synchronization
State can become inconsistent with history after a crash.

The solution:
- use successful `function_call + function_call_output` pairs
- rebuild `completed_steps`
- rebuild `data`
- clear stale transient errors

This makes history the source of truth for the conversation/tool trajectory.

## Completion State
`state.done` represents whether the run already finished successfully.

This value is persisted and should not automatically be reset during history synchronization.

## Final Run States

```text
Fresh Run
Interrupted Run → Resume
Completed Run → Do Not Run Again
```

## Simple Scenarios

### Scenario 1 — File Processing
The agent:
1. lists files
2. reads a file
3. writes a summary
4. verifies it

State tracks completed operations and useful outputs.

### Scenario 2 — Crash During Tool Execution
The process dies after a `function_call` is saved but before its output is saved.

Recovery removes the incomplete call and allows the model to make the decision again.

### Scenario 3 — Resume After Restart
The same `run_id` is passed again.

The agent restores state/history and continues from the last safe point.

## Important Keywords
- Stateful Agent
- Agent State
- Conversation History
- Persistence
- Run ID
- Resume
- Crash Recovery
- Crash Consistency
- Serialization
- Source of Truth
- State Synchronization
- Tool Call
- Function Call Output
- Idempotency
- Lifecycle

## Common Interview Questions

### What is the difference between state and history?
History is the sequence of past events. State is the current snapshot derived from or maintained alongside those events.

### Why is state useful in an agent?
It allows the system to track progress, results, errors, and completion explicitly instead of relying only on the model's conversational context.

### Why use a run ID?
A run ID gives each execution a stable identity so its state and history can be persisted and restored.

### Why persist history as well as state?
State alone may not contain enough conversational/tool context for the model to continue a previous Responses API interaction correctly.

### What is crash consistency?
The property that persisted data remains recoverable and internally valid even if the process stops between related writes.

### Why can an unmatched function call break resume?
The API expects a tool/function call to have a corresponding output before continuing the conversation.

### How can state and history become inconsistent?
A crash may occur after one is saved but before the other is saved.

### How do you recover?
Validate persisted history, remove incomplete tool-call records, then rebuild state from completed successful call/output pairs.

### Why not use LangGraph yet?
The goal was to understand the mechanics manually first: state, persistence, lifecycle, recovery, and resume. Frameworks can be learned afterward with a stronger foundation.
