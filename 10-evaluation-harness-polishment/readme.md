# Project 9 — Evaluation Harness

A simple evaluation runner for testing an AI agent repeatedly and measuring its reliability.

## Structure

```text
project/
├── cases/
│   ├── write_file.json
│   ├── delegate_reader.json
│   └── ...
├── results/
├── runner.py
└── app.py
```

## Test Cases

Put test cases inside the `cases/` folder as JSON files.

Example:

```json
{
  "id": "write_file",
  "input": "Write Hello Agentic World into hello.txt",
  "expected": {
    "tool": {
      "name": "write_file"
    },
    "max_iterations": 3
  },
  "scorers": [
    "tool_called",
    "max_iterations"
  ]
}
```

Each case defines:

* `id` — unique test name
* `input` — prompt sent to the agent
* `expected` — expected behavior
* `scorers` — checks used to evaluate the run

## Available Scorers

Depending on the current implementation:

```text
tool_called
max_iterations
llm_judge
```

Example using LLM Judge:

```json
{
  "id": "explain_dataclass",
  "input": "Explain Python dataclass in a simple and short way.",
  "expected": {
    "answer_rubric": "The answer must be correct, simple and short.",
    "max_iterations": 1
  },
  "scorers": [
    "llm_judge",
    "max_iterations"
  ]
}
```

## Run

Run all cases once:

```bash
python runner.py
```

Run all cases 5 times:

```bash
python runner.py --runs 5
```

Run only one case:

```bash
python runner.py --case write_file
```

Run one case 5 times:

```bash
python runner.py --case write_file --runs 5
```

## Output

The runner reports results such as:

```text
write_file: 80% (4/5 passed)
delegate_reader: 100% (5/5 passed)
```

Detailed reports are saved inside:

```text
results/
```

## Evaluation Flow

```text
Test Cases
    ↓
Runner
    ↓
Agent
    ↓
Scorers
    ↓
PASS / FAIL / ERROR
    ↓
Report
```

## Goal

Measure whether the agent works:

```text
Correctly
Reliably
Efficiently
```

instead of relying on manually watching a single successful run.
