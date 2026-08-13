# Project 10 — Quick Review

## Core Lessons

| Concept | Why it matters |
|---|---|
| Typed `TestCase` / `Expected` | Replaces fragile nested dictionaries with clear domain models. |
| Parse, then validate | Rejects bad JSON cases before spending time or LLM calls. |
| `ToolCall(name, arguments)` trajectory | Preserves every invocation, its inputs, duplicates, and order. |
| Multiple expected calls | Tests multi-step agent behavior, not only one tool name. |
| `ToolCallScorer` | Deterministically checks expected tool names and exact arguments. |
| `ToolOrderScorer` | Checks relative order without requiring an identical trajectory. |
| Structured LLM Judge | Pydantic parses `status`, `reason`, and `score` instead of fragile free text. |
| Setup / cleanup | Makes each case independent of workspace state or execution order. |
| `try/finally` | Guarantees cleanup even when the agent or a scorer raises an error. |
| Repeated runs | Reveals nondeterminism through pass rate instead of trusting one success. |
| Latency | Measures efficiency with `time.perf_counter()` and average duration. |
| Saved reports / regression comparison | Shows behavior changes over time per case. |

Regression statuses: `IMPROVED`, `REGRESSED`, `UNCHANGED`, `NEW`, `REMOVED`.

## Simple Scenarios

1. **Write a file:** expect `write_file` with the correct filename and content.
2. **Delegate, then write:** expect `call_sub_agent` before `write_file`; unrelated calls in between are allowed.
3. **Delete a file safely:** setup creates the file, the agent deletes it, and cleanup restores isolation.
4. **Evaluate a natural-language answer:** a Pydantic-backed LLM Judge applies an answer rubric.
5. **Detect a regression:** run the suite before and after a change, then compare case pass rates and latency.

## Keywords and Tools

`dataclass`, `Pydantic`, `BaseModel`, `Protocol`, `Enum`, JSON, parsing, validation, trajectory, deterministic scorer, LLM-as-Judge, structured output, test isolation, fixture, `try/finally`, repeated runs, pass rate, `mean`, `time.perf_counter`, latency, regression testing, `argparse`.

## Common Interview Questions

**Why evaluate an agent repeatedly?**  
Agents are nondeterministic; repeated runs expose reliability and produce a meaningful pass rate.

**Why prefer deterministic scorers?**  
They are faster, cheaper, reproducible, and easier to debug. Use an LLM Judge only for semantic quality.

**What is an agent trajectory?**  
The ordered record of actions/tool calls, including arguments, taken during a run.

**Exact order or relative order?**  
Relative order is usually less brittle: required actions must appear in sequence, while harmless extra calls remain valid.

**Why validate before execution?**  
It separates invalid test data from agent failures and avoids unnecessary LLM cost and latency.

**How do you isolate agent tests?**  
Each case owns its setup and cleanup; cleanup runs in `finally` so cases cannot leak state.

**Why use Pydantic for an LLM Judge?**  
It enforces a typed output contract and removes fragile string or manual JSON parsing.

**PASS vs FAIL vs ERROR?**  
`PASS`: behavior met expectations. `FAIL`: valid run missed expectations. `ERROR`: evaluation or execution could not complete correctly.

**How is a regression detected?**  
Compare old and new pass rates per case, while treating latency as supporting evidence.

**What was intentionally deferred?**  
Token/cost tracking, partial argument matching, parallel evaluation, CI integration, and advanced report persistence.

## Mental Model

```text
JSON cases → Parse → Validate → Setup → Run → Score → Cleanup
                                              ↓
                              Repeat → Measure → Save → Compare
```
