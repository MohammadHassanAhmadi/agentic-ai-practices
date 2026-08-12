# Project 8 — Sub-agents (Delegation)

An orchestrator agent that delegates focused sub-tasks to a worker agent.

Builds on Project 6 (sandbox, approval gate) and Project 7 (result envelope,
error codes).

---

## 1. What this project does

```
You
 └── Orchestrator                    depth 0
       ├── write_file, delete_file
       ├── call_sub_agent(agent_name, task)
       └── history: your request + one tool result per delegation
             │
             └── reader                depth 1
                   ├── list_files, read_file, search_files
                   └── history: the task string only, discarded at the end
```

A sub-agent is a tool. Inside that tool, a second agent loop runs.

Both agents call the same `run_agent` function. They differ in three inputs
only: system prompt, tool schemas, and depth.

---

## 2. The design decisions

### Who does the writing

The worker is **read-only**. The orchestrator owns `write_file` and
`delete_file`.

Trade-off: the summary text passes through the orchestrator's history, which
is slightly weaker isolation. In exchange, no destructive tool sits behind a
machine caller.

### No overlapping read tools

The orchestrator has **no** read tools. All reading goes through the worker.

This removes an ambiguity: with `read_file` on both agents, the model has two
valid paths for the same job and chooses inconsistently.

Cost: reading one small file now runs a whole extra agent. Acceptable here,
not always acceptable in production.

### What the child receives

The task string only. No parent history.

This is what makes delegation worth doing, and it puts the burden on the
orchestrator to write a complete task.

### What the child returns

`AgentRun` internally. `call_sub_agent` converts it to the Project 7 envelope
before the model sees it.

```
AgentRun   → status, result, error_code, iterations, tools_called
envelope   → {"ok": true, "data": {...}} | {"ok": false, "error": {...}}
```

Same split as a domain model vs a DTO. `iterations` and `tools_called` stay
in the logs — the model cannot act on them, so they would only cost context.

---

## 3. Safety controls

All four are enforced in code. None rely on prompt wording.

| Control | Where | Result when triggered |
|---|---|---|
| Depth cap (`MAX_DEPTH = 1`) | `call_sub_agent`, before spawning | `DELEGATION_NOT_ALLOWED` |
| Iteration cap | `run_agent` loop | `STOPPED` → `SUB_AGENT_STOPPED` |
| Duplicate delegation guard | `run_agent`, per-run `set` | `DUPLICATE_DELEGATION` |
| Unknown agent name | `call_sub_agent` | `INVALID_ARGUMENTS` |

Plus: any exception inside `run_agent` returns `FAILED` / `AGENT_ERROR`
instead of propagating. A sub-agent is a tool, and tools never raise into the
loop.

The approval gate lives in `tools.call_tool` and always reaches the human,
regardless of depth.

---

## 4. Key files

```
app.py             run_agent, call_sub_agent, AGENTS registry, tool schemas
tools.py           file tools, call_tool, envelope, ToolError, approval gate
system_prompts.py  ORCHESTRATOR_SYSTEM_PROMPT, READER_SYSTEM_PROMPT
inputs.py          test inputs
workspace/         the sandbox
```

`tools.py` does not import `app.py`. `call_sub_agent` is dispatched in
`run_agent` before falling through to `tools.call_tool`, which keeps the
dependency one-directional and keeps `depth` out of the file tools.

---

## 5. Test results

All tests pass.

**Group A — no code changes**

| Test | Proves |
|---|---|
| Write `notes.txt` | Orchestrator does simple work itself, no delegation |
| Summarise into `summary.txt` | Delegation end to end; context isolation |
| Search for "budget" | Worker completes a multi-step read task |
| Unknown agent name | Refused without crashing |
| Ask reader to write | Tool narrowing holds |
| Read a missing file | `SUCCESS` with an explanation, not `FAILED` |
| Delete a file | Approval reaches the human at depth 0 |

**Group B — one temporary change each**

| Test | Change | Proves |
|---|---|---|
| Iteration cap | `max_iterations=1` | `STOPPED` → envelope → parent recovers |
| Depth cap | schema + prompt line on reader | `DELEGATION_NOT_ALLOWED` from code |
| Agent crash | `raise RuntimeError` at depth 1 | `FAILED` → `AGENT_ERROR`, app survives |

---

## 6. The failure worth remembering

The first run of the summarise test passed mechanically but failed the point
of the project.

The orchestrator asked the reader to *return the contents* of `notes.txt`.
The reader obeyed. All 551 bytes landed in the orchestrator's history, and
the orchestrator did the summarising itself.

No error. No crash. The architecture was intact and delivered nothing.

The fix was in the prompt, not the code: ask the worker for the finished
result, never for raw content to process yourself.

**A badly written task string silently defeats delegation.**

---

## 7. Known limitations

- The duplicate guard matches exact `(agent_name, task)` pairs. A reworded
  retry slips through. The parent's iteration cap is the real backstop.
- A worker that hits its cap discards partial work. Real systems return what
  they have so the parent can salvage it.
- The tool list is advertising, not enforcement. `call_tool` dispatches from
  one global registry, so a worker asking for `write_file` would get it. Only
  the prompt and the advertised schemas stop it.
