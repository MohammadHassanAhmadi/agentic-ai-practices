# Project 6 — Tools With Real Side Effects

## Primary learning goal

**The model proposes. Your code disposes.**

Every tool so far was pure: text in, text out, nothing happened in the world.
Now the tools touch the filesystem. A wrong call cannot be undone.

Two defences, both written in Python — never in the prompt:

1. A **sandbox** so the agent cannot escape one folder.
2. An **approval gate** so a human confirms before anything destructive runs.

---

## What to build

Start from your Project 5 file.

### 1. Four tools

| Tool | Parameters | Returns |
|---|---|---|
| `list_files` | none | the file names in the sandbox |
| `read_file` | `path` | the file contents |
| `write_file` | `path`, `content` | a short confirmation |
| `delete_file` | `path` | a short confirmation |

Keep the string-in / string-out shape you already have. Your `call_tool` from
Project 3 already turns any exception into an error message for the model, so
these tools can just raise when something is wrong.

### 2. The sandbox

Pick one folder — for example `./workspace/` — and create it on startup.

Every path the model sends must resolve **inside** that folder. If it does not,
raise before touching the disk.

Things the model might send, on purpose or by accident:

```
../secrets.env
/etc/passwd
workspace/../../app.py
notes/../../.env
```

String checks are not enough. `startswith("workspace")` passes for
`workspace/../../.env`. You need to resolve the path to its real absolute form
first, and then compare.

Look at `pathlib.Path` — specifically `.resolve()` and `.is_relative_to()`.

This check belongs in **one** function that every tool calls. Not copied into
four places.

### 3. The approval gate

Before a destructive tool runs, print what is about to happen and ask the user
to confirm with `input()`.

Decisions you have to make:

- Which tools need approval? Reading and listing change nothing. Writing and
  deleting do. Where exactly is the line?
- If the user says no, what does the tool return? Remember: whatever you
  return goes back to the model as a tool result, so it must make sense to the
  model.
- Where does the gate live — inside each tool, or in one place that wraps them?

Think about the last one carefully. The wrong answer means a future tool you
add is unprotected by default.

### 4. Watch out for the trap

You are still running scripted test cases in a loop. `input()` blocks and waits
for a human. Decide how you want to handle that while testing.

---

## Expected behaviour

- The agent can create, read, list and delete files inside the sandbox.
- Any path outside the sandbox is refused, and the model is told why.
- Nothing destructive happens without a human typing yes.
- A refusal is a normal tool result, not a crash. The agent should explain it
  and carry on.

---

## Concepts you are practising

**Trust boundary.** The model's output is untrusted input. Treat a tool
argument the way you treat a query string parameter in ASP.NET — validate it,
never assume it is well-formed or well-intentioned.

**Validation in code, not in the prompt.** You could write "never access files
outside the workspace" in the system prompt. It would mostly work. That is the
problem — mostly is not a security control. A prompt is a request; code is a
guarantee.

**Human in the loop.** Autonomy is a spectrum, not a switch. Read-only actions
can run freely. Destructive ones need a gate. Choosing where that line sits is
a design decision, and it is the interesting part of this project.

**Irreversibility.** Some operations cannot be retried. That changes how you
handle failure: for a pure tool, retrying is free; for `delete_file`, being
wrong once is permanent.

---

## Why this matters for your career

| | |
|---|---|
| **Skill** | Safe tool design for agents with real-world effects |
| **Where it is used** | Every coding agent, deployment bot, and internal automation agent |
| **Interview question** | "How do you stop an agent from doing something destructive?" The answer is a trust boundary in code plus a human gate — not prompt instructions |
| **Different in production** | Container or VM isolation instead of a path check, an allowlist of permitted operations, an audit log of every tool call, dry-run modes, and permission tiers per user |

---

## Optional extension

Add a "remember this approval" option, so approving `write_file` once approves
it for the rest of the session. This is how real coding agents work — and it is
worth thinking about what that convenience costs you.

---

## Done when

- Every escape attempt in the list above is refused.
- No destructive action runs without approval.
- Adding a new destructive tool would be protected automatically, without you
  remembering to add a check.
