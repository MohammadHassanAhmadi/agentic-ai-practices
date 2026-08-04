# Planning Agent

A simple educational project for learning the fundamentals of **Agentic AI**.

This project demonstrates how an AI agent can first **plan** a task using an LLM and then **execute** that plan step by step.

> **This project is designed for learning, not production use.**

---

## Learning Objectives

By completing this project, you will understand:

- Tool Routing
- Planning
- Sequential Execution
- Data Flow between tools
- Separation of Planner and Executor

---

## Project Architecture

```
User
   │
   ▼
Planner (LLM)
   │
   ▼
Execution Plan (JSON)
   │
   ▼
Executor (Python)
   │
   ▼
Tools
```

---

## Available Tools

- `count_words`
- `convert_to_uppercase`
- `summarize_text`
- `extract_keywords`

---

## Example Plan

```json
{
  "steps": [
    {
      "action": "summarize_text",
      "input": "Artificial Intelligence is changing software development."
    },
    {
      "action": "extract_keywords"
    }
  ]
}
```

---

## Project Structure

```
planning_agent/
│
├── app.py
├── planner_prompt.txt
├── README.md
└── ...
```

---

## How It Works

1. The user enters a request.
2. The Planner analyzes the request.
3. The Planner returns a structured JSON plan.
4. The Executor executes each step in order.
5. The output of one step becomes the input of the next step.
6. The final result is returned to the user.

---

## Example Workflow

```
User
    │
    ▼
Summarize this text and extract keywords.

    │
    ▼
Planner

    │
    ▼
summarize_text
        ↓
extract_keywords

    │
    ▼
Executor

    │
    ▼
Summary

    │
    ▼
Keywords
```

---

## Important Design Principle

The project follows a clear separation of responsibilities:

- **Planner** decides **what** should be done.
- **Executor** decides **nothing**. It simply executes the plan.

---

## Current Limitations

This educational project intentionally supports only **linear execution**.

Supported:

```
A
↓
B
↓
C
```

Not supported:

```
      A
     / \
    B   C
```

Branching workflows and dependency graphs will be introduced in future projects.

---

## Future Learning Projects

- Memory
- RAG
- Tool Calling
- Multi-Agent Systems
- MCP
- Reflection
- Planning with Dependencies

---

## License

This repository is intended for educational purposes.