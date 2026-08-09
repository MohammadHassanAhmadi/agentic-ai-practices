# Project 8 — Multi-Agent Delegation

Review notes. Concepts only.

---

## Concept 1 — A sub-agent is a tool

**Simple explanation**

Delegation is not a new mechanism. You register a tool called
`call_sub_agent`. Inside that tool, a second agent loop runs. The parent sees
a normal tool result and never knows an agent was involved.

**Problem it solves**

It makes multi-agent systems recursive rather than architectural. If you can
write a tool and a loop, you can write a multi-agent system. No framework
needed.

**How to implement**

- Extract the loop into a function taking `system_prompt`, `tools`, `task`,
  `max_iterations`, and `depth`.
- Store agent definitions in a registry: name → prompt + tool schemas.
- `call_sub_agent` looks up the agent, runs the loop, converts the result.

**Best practices**

- One loop function for every agent. Two copies drift apart.
- The parent's tool schema for `call_sub_agent` takes `agent_name` and `task`
  only. Everything else comes from your code.

---

## Concept 2 — Context isolation is the reason to delegate

**Simple explanation**

The child gets the task string and nothing else. Its history is discarded
when it finishes. Only its final answer enters the parent's context.

**Problem it solves**

A single agent accumulates every intermediate step. Reading five files leaves
five file contents in the window. Trimming (Project 5) treats the symptom;
isolation removes the cause.

**How to implement**

- Child history starts empty inside `run_agent`.
- Never pass the parent's messages down.
- Return only what the parent can act on. Diagnostics stay in logs.

**Best practice**

Verify it. Print the parent's history after a delegation and count the
entries. If the child's tool outputs appear there, isolation is broken.

---

## Concept 3 — The task string is the real interface

**Simple explanation**

The child has no context except the task text. So the parent's ability to
write a complete, self-contained instruction determines whether delegation
works.

**Problem it reveals**

Delegation can fail *silently*. If the parent asks the worker to "return the
contents of the file", the worker becomes a proxy. The parent's context fills
up anyway, and the parent does the real work. No error is raised. The
architecture is intact and useless.

**How to implement**

Instruct the parent explicitly:

- Ask for the finished result, not raw material to process.
- Include exact file names and paths.
- State what the worker should return.

**Best practice**

Treat the task string like a tool description. It is a contract written at
runtime by a model, which makes it the least reliable part of the system.

---

## Concept 4 — Safety controls belong in code

**Simple explanation**

Depth caps, iteration caps, and duplicate guards must be enforced in your
dispatcher, not requested in a prompt. A prompt advises. Code enforces.

**Problem it solves**

Runaway recursion and retry loops. Both cost money and neither is bounded by
anything the model chooses to respect.

**How to implement**

| Control | Where it lives |
|---|---|
| Depth cap | `call_sub_agent`, checked before spawning a child |
| Iteration cap | inside the loop |
| Duplicate guard | per-run `set` of `(agent_name, task)` in the parent's loop |

`depth` is a parameter of your loop, never a tool argument. If the model can
send it, the model controls the limit, and it is not a control.

**Best practice**

Test each control by making the model actually attempt the forbidden action.
A control that has never fired is unverified.

---

## Concept 5 — Errors cross the agent boundary as data

**Simple explanation**

A sub-agent is a tool, so its failures return in the same envelope as any
other tool error. Exceptions never propagate from child to parent.

**Problem it solves**

One failing worker would otherwise crash the whole system. Instead, the
parent reads an error code and decides: retry with a different task, or
explain and stop.

**How to implement**

- Internal type (`AgentRun`) with status, result, and error code.
- Convert to the envelope at the tool boundary.
- Catch broadly inside the loop. Return `FAILED` with a safe message; never
  leak the raw exception text to the model.

**Design point**

Distinguish two questions:

```
Did the loop finish cleanly?    → status (COMPLETED / STOPPED / FAILED)
Did the task actually succeed?  → the answer text, read by the parent
```

A worker reporting "file not found" is `COMPLETED`, not `FAILED`. Collapsing
these causes pointless retries.

---

## Concept 6 — Trust does not inherit downward

**Simple explanation**

The approval gate exists to put a human in the loop. When the caller becomes
a machine, the gate must still reach the human. A parent agent approving its
child's destructive action removes the human entirely.

**How to implement**

Keep the gate in the tool dispatcher, below all agent logic. Depth is
irrelevant to it.

**Related design choice**

Deciding which agent holds destructive tools:

| Worker | Isolation | Blast radius |
|---|---|---|
| Read-only, parent writes | weaker | small |
| Worker writes | stronger | larger |

There is no correct answer. Read-only workers are the safer default.

---

## Concept 7 — Advertising is not enforcement

**Simple explanation**

The tool schema list tells the model what it may call. The dispatcher decides
what actually runs. If the dispatcher uses one global registry, a narrow tool
list is a suggestion, not a boundary.

**Best practice**

For real isolation, pass the allowed tool set into the dispatcher and reject
anything outside it. Advertising alone is fine for learning, but know which
one you have.

---

## Where this pattern fits

Project 8 covers **orchestrator → worker**, the simplest multi-agent shape.

Others build on it:

| Pattern | Idea |
|---|---|
| Map-reduce | one parent, many parallel workers, merged results |
| Peer / A2A | agents call each other, no fixed hierarchy |
| Critic loop | one agent produces, another reviews, repeat |
| Planner-executor | one agent plans steps, another carries them out |

All of them are the same primitive: an agent exposed as a tool.

---

## Tools and topics to learn next

- **Evaluation harness** — scoring agent runs on a fixed task set. Without
  it, "did the change help?" is guesswork.
- **Partial results on timeout** — returning what a stopped worker did
  accomplish, not just the stop reason.
- **Parallel delegation** — running independent workers concurrently
  (`asyncio` in Python).
- **Tracing** — structured run logs across depths. LangSmith, Langfuse, or
  OpenTelemetry. Your `iterations` / `tools_called` fields are the first step
  toward this.
- **Framework comparison** — read how LangGraph, CrewAI, and the OpenAI
  Agents SDK model delegation. Read them *after* building your own, to
  recognise the trade-offs they made.