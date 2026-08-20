# Agentic AI Practices

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-compatible-412991?logo=openai&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-framework-1C3C3C)
![RAG](https://img.shields.io/badge/RAG-Chroma%20%2B%20Embeddings-6B46C1)

## Overview

A hands-on portfolio of **16 progressively built projects** completed during a focused, 100-hour study and implementation track in Agentic AI and LLM application engineering.

The work follows a deliberate path: understand the mechanism, implement it from scratch, verify it with tests, then compare it with a production-oriented framework. The result is a practical foundation in building agents that can use tools safely, delegate work, retain state and memory, and answer questions from persistent knowledge bases.

## What this demonstrates

- Designing agent loops, planning and sequential execution
- OpenAI-compatible tool calling with structured arguments and typed results
- Secure filesystem tools with sandbox boundaries and human approval gates
- Multi-agent delegation and role-based orchestration
- Evaluation harnesses with deterministic scoring, LLM judging, repeated runs, latency and regression comparison
- Stateful agents with persistence, crash recovery and safe resume
- LangGraph graphs, conditional routing, tool nodes, checkpoints and interrupts
- Long-term memory with user isolation, CRUD, deduplication and process-restart persistence
- RAG pipelines with local embeddings, semantic retrieval, grounding and validated citations
- Production-oriented RAG with chunking, Chroma persistence and separate ingestion/query workflows

## Project progression

| # | Project | Main capability |
|---:|---|---|
| 01 | Plan and Execute | LLM-generated plans and deterministic step-by-step execution |
| 02 | Agent Loop | The basic request → model → tool/result loop |
| 03 | Using Tools | Tool schemas, routing and execution |
| 04 | Memory and Context | Passing context through an agent workflow |
| 05 | Context Management | Chained tool calls and interaction logging |
| 06 | File Tools | Real side effects, path sandboxing and approval gates |
| 07 | Structured Output | Argument validation, typed results and machine-readable errors |
| 08 | Sub-agents | Delegation between an orchestrator and specialist agent |
| 09 | Evaluation Harness | Test cases as data, scorers, repeated runs and reports |
| 10 | Evaluation Polish | Typed trajectories, tool-order scoring, LLM judge and regression analysis |
| 11 | Stateful Agent | Persisted state/history, crash recovery and resume |
| 12 | Stateful Agent with LangGraph | Graph execution, SQLite checkpoints and interrupts |
| 13 | Long-term Memory | Durable user memories built from scratch |
| 14 | Long-term Memory with LangGraph | Store abstraction, runtime context and SQLite persistence |
| 15 | Minimal RAG | Embeddings, cosine similarity, grounding and verified sources |
| 16 | Persistent Vector RAG | File ingestion, overlapping chunks, Chroma and retrieval across processes |

## Technical stack

Python · OpenAI-compatible APIs · Azure OpenAI · Pydantic · LangChain · LangGraph · Sentence Transformers · ChromaDB · SQLite · JSON persistence · pytest-style deterministic tests · evaluation and regression tooling

## Engineering approach

The projects intentionally expose the important design decisions instead of hiding them behind abstractions. For example, Project 11 implements state persistence and recovery manually before Project 12 maps the same responsibilities to LangGraph. Similarly, Project 15 builds the RAG retrieval path directly before Project 16 introduces real files, chunking and a persistent vector store.

The final RAG project also documents a known retrieval limitation and identifies appropriate next steps—hybrid search, reranking and query rewriting—rather than treating every failed retrieval as a prompt problem.

## Repository structure

Each numbered directory contains the implementation, test cases or evaluation data, and focused documentation for that stage.

```text
01-plan-and-execute/
...
09-evaluation-harness/
10-evaluation-harness-polishment/
11-stateful-agent/
12-stateful-agent-LangGraph/
13-long-term-memory-agent/
14-long-term-memory-framework/
15-RAG/
16-RAG-vector-persistance/
shared_tools/
```

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Configure the required Azure/OpenAI environment variables in a local `.env` file, then run the entry point inside the project you want to explore. For Project 16, ingest the documents first and then query the persistent store:

```bash
cd 16-RAG-vector-persistance
python ingest.py
python ask.py
```

## Scope

This repository is a learning and portfolio project, not a production service. Its value is the progression from fundamentals to framework-based implementations, explicit validation and safety boundaries, reproducible evaluation, and honest documentation of limitations.

