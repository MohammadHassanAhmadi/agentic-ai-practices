# Project 10 — Polished Evaluation Harness

A small evaluation harness for measuring an AI agent's correctness, reliability, and latency across repeated runs.

## Goal

Measure whether the agent works:

```text
Correctly
Reliably
Efficiently
```

## What Was Added

- Typed `TestCase`, `Expected`, and `ToolCall` models
- JSON parsing and validation before agent execution
- Tool-call arguments, multiple expected calls, and relative-order checks
- Deterministic scorers plus a structured Pydantic LLM Judge
- Isolated tests with setup, cleanup, and `try/finally`
- Repeated runs, latency measurement, saved reports, and regression comparison

## Add Test Cases

Place one JSON file per case inside `cases/`:

```text
cases/
├── write_file.json
└── delegate_then_write.json
```

Example:

```json
{
  "id": "delegate_then_write",
  "input": "Read notes.txt, then write its summary to summary.txt.",
  "setup": {
    "create_files": {
      "notes.txt": "Agent evaluation notes"
    }
  },
  "expected": {
    "tool_calls": [
      {
        "name": "call_sub_agent",
        "arguments": {}
      },
      {
        "name": "write_file",
        "arguments": {
          "filename": "summary.txt"
        }
      }
    ],
    "max_iterations": 4,
    "answer_rubric": "The answer must clearly confirm the completed task."
  },
  "scorers": [
    "tool_calls",
    "tool_order",
    "max_iterations",
    "llm_judge"
  ]
}
```

Only include expectations and scorers needed by the case. `tool_calls` uses exact argument matching when `arguments` is not empty. `tool_order` checks relative order, so unrelated calls may appear between expected calls.

## Run Evaluations

```bash
# Run every case once
python runner.py

# Run every case five times
python runner.py --runs 5

# Run one case five times
python runner.py --case delegate_then_write --runs 5
```

Reports are saved as JSON files under `results/`. Each report includes pass rates and average duration.

## Compare Reports

After creating at least two reports:

```bash
python run_evaluator.py
```

The latest two reports are compared per case as `IMPROVED`, `REGRESSED`, `UNCHANGED`, `NEW`, or `REMOVED`. Status is based on pass rate; latency is shown as a supporting metric.

> Token and cost tracking were intentionally deferred.


