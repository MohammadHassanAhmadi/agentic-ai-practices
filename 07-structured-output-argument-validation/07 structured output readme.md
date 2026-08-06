# Project 7 — Structured Output and Argument Validation

## Goal

A tool call goes in two directions:

```
model  --(arguments)-->  your tool
model  <--(result)----   your tool
```

Right now both directions are plain strings, and you accept whatever arrives.
This project fixes both.

### Direction 1 — arguments coming in

`strict: True` checks the **shape** of the arguments: correct keys, correct
types. It does not check the **values**.

So the model can legally send `path = ""` or `max_lines = 999999999`.
The schema is happy. Your code is not.

**Fix:** check the values yourself, before the tool runs.

### Direction 2 — result going out

Today `read_file` returns the file content as a string.
If the file is missing, it returns `"Error: file not found"` — also a string.

The model receives a string in both cases. It cannot tell if that text is the
file, or a message about the file.

**Fix:** return an object with fields. One field says if it worked. Another
holds the data. The status is no longer hidden inside the text.

Both fixes are code, not prompt.

---

## What to build

Start from your Project 6 code.

### 1. One result shape for every tool

Every tool returns the same structure:

```
success  ->  { "ok": true,  "data": ... }
failure  ->  { "ok": false, "error": { "code": ..., "message": ... } }
```

`call_tool` turns this into JSON before sending it as `function_call_output`.

Two things to decide:

- Does the tool return only the data, and `call_tool` adds the wrapper?
  Or does each tool build the full wrapper itself?
- Your sandbox raises `ValueError` today. Who turns that into an error result?

Same answer as in a .NET API: **one place** turns exceptions into responses.
Not thirty places.

### 2. Error codes

The message is for the human. The code is for the machine.

| Code | When |
|---|---|
| `PATH_OUTSIDE_WORKSPACE` | sandbox refused |
| `FILE_NOT_FOUND` | path is valid but no file there |
| `USER_DENIED` | approval gate refused |
| `INVALID_ARGUMENT` | validation failed |
| `FILE_TOO_LARGE` | see below |

Why codes matter: you can write real rules in Python.
"If code is `USER_DENIED`, stop the loop" works.
"If the message contains the word denied" does not.

### 3. Split validation from execution

Right now `read_file` checks things inside itself. Separate the steps:

```
parse args  ->  validate  ->  run  ->  wrap result
```

Validation checks what JSON Schema cannot:

- path is not empty or only spaces
- path is not absolute
- content is not too big
- numbers are inside a sensible range

A validation failure must **not** crash. It returns an `INVALID_ARGUMENT`
result, and the model can try again with better arguments.

### 4. Truncation

Add a size limit to `read_file` — for example 8 KB.

If the file is bigger, return part of it and add a flag:

```
{ "ok": true, "data": { "content": "...", "truncated": true, "total_bytes": 41234 } }
```

This is the main reason structured output exists. You cannot clearly say
"this text is incomplete" *inside* the text. As a separate field, it is clear.

### 5. One new tool: `search_files`

Parameters: `query`, and maybe `max_results`.
Returns a list of matches — file name, line number, the matching line.

This tool is here because a list of records is ugly as text and easy as JSON.
Build it last, after the result shape works.

---

## Python you need

Look these up before you start.

| Python | .NET equivalent |
|---|---|
| `dataclasses.dataclass` | `record` |
| `enum.Enum` | `enum` |
| `typing.TypedDict` | a small DTO with named fields |
| `json.dumps(obj, indent=2)` | `JsonSerializer.Serialize` |
| your own exception class | `class ToolException : Exception` |

**Not required, just so you know it exists:** `pydantic`. It is close to
FluentValidation plus System.Text.Json in one library, and every agent framework
uses it. Write the validation by hand this time. Use pydantic later, when you
know what it replaces.

---

## Questions to answer first

Write your answers in your notes before you code. These are the real exercise.

1. Does `list_files` return `["a.txt", "b.txt"]` or
   `[{"name": "a.txt", "bytes": 120}]`? What does the extra field cost?
2. Should the JSON you send to the model be indented or compact?
   (Think about the cost on every turn.)
3. Is `USER_DENIED` an error, or a normal result that happens to be "no"?
   Your answer changes how the model reacts.
4. When validation fails, do you tell the model exactly why, or only that it
   failed? What is the risk of each?

---

## Done when

- Every tool returns the same result shape. Nothing crashes out of `call_tool`.
- A sandbox violation comes back as `PATH_OUTSIDE_WORKSPACE`, not a stack trace.
- A big file returns partial content with `truncated: true`, and the model
  **tells the user** instead of pretending it read everything.
- `search_files` returns a list the model can count and summarise.
- Your Project 6 tests still pass, unchanged.

---

## Test cases

```python
TEST_CASES = [
    # Setup
    "Create notes.txt with the content: hello agentic world",

    # Normal case, structured result
    "What files exist, and how big are they?",

    # Validation failure - empty path
    "Read the file with an empty name",

    # Error code - file does not exist
    "Read missing.txt",

    # Sandbox - now a code, not a crash
    "Read the file ../.env",

    # Truncation - create a big file by hand in workspace/ first
    "Read big.txt and tell me if you got all of it",

    # Structured list output
    "Search all files for the word hello",
]
```

The truncation test is the important one. If the model says it read the whole
file, then your flag is not reaching it — or your system prompt never explained
what `truncated` means.