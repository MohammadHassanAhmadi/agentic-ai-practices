# Project 5 — Context Window Management

## Primary learning goal

**Your history cannot grow forever. You must decide what to keep.**

Project 4 gave the agent memory. But that memory grows with every turn, and
every turn resends all of it. Cost grows quadratically. Eventually the request
is larger than the model's context window and the API rejects it.

The API does not trim for you. Trimming is your job.

---

## What to build

Start from your Project 4 file.

### 1. Add a size limit

Pick a small limit so you can actually test it — for example, keep at most
**8 messages** in history.

Real systems count tokens, not messages. Counting messages is a simplification
so you can focus on the logic. Note the difference; you do not need to
implement token counting.

### 2. Trim before each API call

Before sending, check the size. If it is over the limit, drop the oldest
messages until it fits.

### 3. Respect the pairing rule

This is the hard part.

A `function_call` and its `function_call_output` are a pair, matched by
`call_id`. If your cut lands between them, you send an orphan and the API
returns an error.

So your trim must find a **safe cut point**, not just slice at a fixed index.

Think about which message types are safe to start a history with, and which
are not.

### 4. Print what you dropped

Show how many messages were removed and how many remain. You cannot debug what
you cannot see.

---

## Expected behaviour

- The agent runs a long conversation without the history growing without bound.
- The API never returns a "missing tool call" style error.
- The agent forgets old facts. **This is correct behaviour, not a bug.**
  Test 4 in `inputs.json` exists to prove the forgetting works as designed.

---

## Optional extension (only after the above works)

Instead of dropping old messages, summarize them.

Send the old messages to the model in a separate call and ask for a short
summary. Replace them with one message containing that summary.

This keeps the meaning but costs an extra API call per compaction. Real agent
frameworks do exactly this and call it "compaction".

---

## Concepts you are practising

**Bounded state.** Any long-running process needs a cap on its state. Same
reason you cap a queue or a cache in .NET — unbounded growth is a bug waiting
to happen.

**Structural invariants.** The `function_call` / `function_call_output` pairing
is an invariant. Your trim function must preserve it. This is the same
discipline as never leaving a transaction half-committed.

**Lossy by design.** Trimming loses information on purpose. The engineering
question is not "how do I avoid losing anything" but "what is safe to lose".

---

## Why this matters for your career

| | |
|---|---|
| **Skill** | Context window management |
| **Where it is used** | Every production agent. It is the top cause of both runaway cost and hard crashes |
| **Interview question** | "Your agent runs for 200 turns. What breaks and how do you fix it?" |
| **Different in production** | Token counting instead of message counting, summarization instead of dropping, pinned system messages that are never trimmed, and moving old context to external storage the agent can search |

---

## Done when

- A long conversation runs with history staying under your limit.
- No orphaned tool call errors, ever.
- You can explain why cutting at an arbitrary index is unsafe.
