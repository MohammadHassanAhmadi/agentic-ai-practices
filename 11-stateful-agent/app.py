import json
import os
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

import tools
from dotenv import load_dotenv
from openai import OpenAI
from system_prompts import ORCHESTRATOR_SYSTEM_PROMPT, READER_SYSTEM_PROMPT

from shared_tools.utiles import Color, configure_utf8_output, print_color

configure_utf8_output()

load_dotenv(override=True)

MAX_ATTEMPTS = 5
MAX_DEPTH = 1


def get_env_var(variable_name: str) -> str:
    value = os.getenv(variable_name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {variable_name}")

    return value


# Create the sandbox workspace when the app starts.
tools.WORKSPACE_PATH.mkdir(exist_ok=True)

openai_api_key = get_env_var("AZURE_OPENAI_API_KEY")
openai_endpoint = get_env_var("AZURE_OPENAI_ENDPOINT")
model = get_env_var("AZURE_OPENAI_MODEL")

client = OpenAI(api_key=openai_api_key, base_url=openai_endpoint)


class RunStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    STOPPED = "stopped"
    PENDING = "pending"


@dataclass
class AgentState:
    current_step: str = ""
    completed_steps: list[str] = field(default_factory=list)
    data: dict = field(default_factory=dict)
    error: str | None = None
    done: bool = False


@dataclass
class ToolCall:
    name: str
    arguments: dict = field(default_factory=dict)


@dataclass
class AgentRun:
    status: RunStatus = RunStatus.PENDING
    result: str = ""
    error_code: str | None = None
    iterations: int = 0
    tools_called: list[ToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    state: AgentState | None = None


def append_to_history(history: list[Any], items: Any) -> None:
    if isinstance(items, list):
        history.extend(items)
    else:
        history.append(items)


CALL_SUB_AGENT_SCHEMA = {
    "type": "function",
    "name": "call_sub_agent",
    "strict": True,
    "description": "Delegate a task to a specialized worker agent.",
    "parameters": {
        "type": "object",
        "properties": {
            "agent_name": {
                "type": "string",
                "description": "Name of the worker agent.",
            },
            "task": {
                "type": "string",
                "description": "Complete task for the worker.",
            },
        },
        "required": ["agent_name", "task"],
        "additionalProperties": False,
    },
}


def call_sub_agent(agent_name: str, task: str, depth: int) -> AgentRun:
    if depth + 1 > MAX_DEPTH:
        return AgentRun(
            status=RunStatus.FAILED,
            error_code=tools.ErrorCode.DELEGATION_NOT_ALLOWED,
            result="Can't Delegate at this level",
        )

    if agent_name not in AGENTS:
        return AgentRun(
            status=RunStatus.FAILED,
            error_code=tools.ErrorCode.INVALID_ARGUMENTS,
            result=f"Unknown agent: {agent_name}",
        )

    agent = AGENTS[agent_name]

    return run_agent(
        agent_name,
        system_prompt=agent["prompt"],
        task=task,
        tool_schemas=agent["tool_schemas"],
        max_iterations=MAX_ATTEMPTS,
        depth=depth + 1,
    )


READER_TOOLS = [tools.list_files, tools.read_file, tools.search_files]
READER_TOOL_SCHEMAS = [
    tools.LIST_FILES_SCHEMA,
    tools.READ_FILE_SCHEMA,
    tools.SEARCH_FILES_SCHEMA,
]

AGENTS = {
    "reader": {"prompt": READER_SYSTEM_PROMPT, "tool_schemas": READER_TOOL_SCHEMAS}
}

ORCHESTRATOR_FUNCTIONS = [call_sub_agent, tools.write_file, tools.delete_file]
ORCHESTRATOR_TOOL_SCHEMAS = [
    CALL_SUB_AGENT_SCHEMA,
    tools.WRITE_FILE_SCHEMA,
    tools.DELETE_FILE_SCHEMA,
]


def get_client():
    return OpenAI()


def to_result_envelope(run: AgentRun) -> dict:
    if run.status == RunStatus.SUCCESS:
        return {
            "ok": True,
            "data": {
                "status": run.status.value,
                "result": run.result,
                "iterations": run.iterations,
                "tool_calls": [asdict(call) for call in run.tools_called],
            },
        }
    return {
        "ok": False,
        "error": {
            "code": run.error_code or "SUB_AGENT_STOPPED",
            "message": run.result,
        },
    }


def build_state_context(state: AgentState) -> str:
    return f"""
Current agent state:
- current_step: {state.current_step}
- completed_steps: {state.completed_steps}
- data: {state.data}
- error: {state.error}
- done: {state.done}
"""


def save_state(run_id: str, state: AgentState) -> None:
    Path("states").mkdir(exist_ok=True)

    path = Path("states") / f"{run_id}.json"

    path.write_text(
        json.dumps(asdict(state), indent=2),
        encoding="utf-8",
    )
    print_color(f"state saved, run_id:'{run_id}'", Color.PINK)


def load_or_create_state(run_id: str) -> AgentState:
    print_color(f"****************Loading state for run_id:{run_id}", Color.PINK)
    path = Path("states") / f"{run_id}.json"

    if not path.exists():
        print_color(f"load path does not exist: '{path}'", Color.PINK)
        return AgentState()  # Return New one when no such a state\

    stat_data_str = path.read_text(encoding="utf-8")
    data = json.loads(stat_data_str)

    return AgentState(**data)


def serialize_history(history: list) -> list:
    serialized = []
    for item in history:
        if hasattr(item, "model_dump"):
            serialized.append(item.model_dump(exclude_none=True))
        else:
            serialized.append(item)
    return serialized


def save_history(run_id: str, history: list) -> None:
    run_path = Path("runs") / run_id
    run_path.mkdir(parents=True, exist_ok=True)

    path = run_path / "history.json"

    serialized = serialize_history(history=history)

    path.write_text(json.dumps(serialized, indent=2), encoding="utf-8")


def recover_history(history: list) -> list:
    if not history:
        return history

    function_outputs = {
        item["call_id"]
        for item in history
        if isinstance(item, dict) and item.get("type") == "function_call_output"
    }
    recovered = []

    for item in history:
        if (
            isinstance(item, dict)
            and item.get("type") == "function_call"
            and item.get("call_id") not in function_outputs
        ):
            continue

        recovered.append(item)

    return recovered


def load_history(run_id: str) -> list[Any]:
    path = Path("runs") / run_id / "history.json"

    if not path.exists():
        print("nothing to load")
        return []
    history = json.loads(path.read_text(encoding="utf-8"))
    print()
    print("Loaded history items:", len(history))
    print()

    return json.loads(path.read_text(encoding="utf-8"))


def sync_state_with_history(
    state: AgentState,
    history: list,
) -> AgentState:
    calls_by_id = {}
    print_color("syncing state with history", Color.YELLOW)
    for item in history:
        if isinstance(item, dict) and item.get("type") == "function_call":
            calls_by_id[item["call_id"]] = item

    completed_steps = []
    data = {}

    for item in history:
        if not isinstance(item, dict) or item.get("type") != "function_call_output":
            continue

        call_id = item["call_id"]
        call = calls_by_id.get(call_id)

        if call is None:
            continue

        output = json.loads(item["output"])

        if output.get("ok") is True:
            tool_name = call["name"]

            completed_steps.append(tool_name)
            data[tool_name] = output

    state.completed_steps = completed_steps
    state.data = data
    state.current_step = ""
    state.error = None

    print_color("sync completed!", Color.YELLOW)

    return state


def run_agent(
    agent_name: str,
    system_prompt: str,
    task: str,
    tool_schemas: list,
    max_iterations: int = MAX_ATTEMPTS,
    depth: int = 0,
    run_id: str | None = None,
) -> AgentRun:

    tools_called: list[ToolCall] = []
    failed_delegations: set[tuple[str, str]] = set()

    if run_id is None:
        run_id = str(uuid4())

    print_color(f"Running task with run_id:{run_id}", color=Color.PINK)
    print()

    state = load_or_create_state(run_id)

    history_messages = load_history(run_id)

    before = len(history_messages)
    history_messages = recover_history(history_messages)
    after = len(history_messages)
    print(f"Recovered history: {before} → {after}")

    state = sync_state_with_history(
        state,
        history_messages,
    )

    if state.done:
        print_color(
            f"task with run_id:{run_id} already completed. no more effort", Color.PURPLE
        )
        return AgentRun(
            state=state,
            status=RunStatus.SUCCESS,
            iterations=0,
            tools_called=[],
            result="Run already completed",
        )
    else:
        print_color(
            f"task with run_id:{run_id} is not yet completed. needs more effort",
            Color.PURPLE,
        )

    save_state(run_id, state)
    save_history(run_id, history_messages)

    if (
        not history_messages
    ):  # if task was loaded in history, no need to add again, otherwise we need to add
        append_to_history(
            history_messages,
            {"role": "user", "content": task},
        )
        save_history(run_id, history_messages)
    try:
        for agent_attempt in range(max_iterations):
            print_color(
                f" [{agent_name}] → "
                f"(Attempt {agent_attempt + 1}/{max_iterations} | Depth {depth})",
                Color.GRAY,
            )

            state_context = build_state_context(state)
            instructions = f"""
{system_prompt}

{state_context}
"""
            llm_resp = client.responses.create(
                model=model,
                tools=tool_schemas,
                instructions=instructions,
                input=history_messages,
            )

            append_to_history(history_messages, llm_resp.output)
            save_history(run_id, history_messages)
            tool_was_called = False

            for item in llm_resp.output:
                if item.type != "function_call":
                    continue

                tool_was_called = True
                state.current_step = item.name

                arguments = json.loads(item.arguments)

                tools_called.append(
                    ToolCall(
                        name=item.name,
                        arguments=arguments,
                    )
                )

                # -------------------------
                # Execute tool
                # -------------------------

                if item.name == "call_sub_agent":
                    key = (
                        arguments["agent_name"],
                        arguments["task"],
                    )

                    if key in failed_delegations:
                        run = AgentRun(
                            status=RunStatus.FAILED,
                            error_code="DUPLICATE_DELEGATION",
                            result=(
                                "This exact task already failed. "
                                "Change the task or do it yourself."
                            ),
                        )
                    else:
                        run = call_sub_agent(
                            agent_name=arguments["agent_name"],
                            task=arguments["task"],
                            depth=depth,
                        )

                    result = to_result_envelope(run)

                    tool_succeeded = run.status == RunStatus.SUCCESS

                    if not tool_succeeded:
                        failed_delegations.add(key)
                        state.error = run.error_code or run.result

                else:
                    result = tools.call_tool(
                        item.name,
                        item.arguments,
                    )

                    tool_succeeded = result.get("ok", False)

                    if not tool_succeeded:
                        error = result.get("error", {})
                        state.error = error.get(
                            "message",
                            "Tool execution failed",
                        )

                # -------------------------
                # Update state
                # -------------------------

                if tool_succeeded:
                    state.completed_steps.append(item.name)
                    state.error = None
                    state.data[item.name] = result
                    save_state(run_id, state)

                append_to_history(
                    history_messages,
                    {
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": json.dumps(result),
                    },
                )
                save_history(run_id, history_messages)

                print_color(
                    f"[TOOL] result: {result}",
                    Color.GRAY,
                )

            # No tool call = final answer
            if not tool_was_called:
                state.done = True
                state.current_step = ""
                save_state(run_id, state)
                print_color(
                    f"{agent_name} → {llm_resp.output_text}",
                    Color.GREEN,
                )

                return AgentRun(
                    status=RunStatus.SUCCESS,
                    result=llm_resp.output_text,
                    iterations=agent_attempt + 1,
                    tools_called=tools_called,
                    state=state,
                )

        # Max iterations
        state.error = "Max iterations reached"
        save_state(run_id, state)
        return AgentRun(
            status=RunStatus.STOPPED,
            result="Max iterations reached",
            iterations=max_iterations,
            tools_called=tools_called,
            state=state,
        )

    except KeyboardInterrupt:
        state.error = "Agent stopped by user"
        save_state(run_id, state)
        return AgentRun(
            status=RunStatus.STOPPED,
            result="Agent stopped by user",
            iterations=0,
            tools_called=tools_called,
            state=state,
        )

    except Exception as e:
        state.error = str(e)
        save_state(run_id, state)
        print_color(
            f"[{agent_name}] failed: {e!r}",
            Color.RED,
        )

        return AgentRun(
            status=RunStatus.FAILED,
            error_code="AGENT_ERROR",
            result="The agent failed unexpectedly.",
            tools_called=tools_called,
            state=state,
        )


def run_agent_for_runner(user_prompt: str) -> AgentRun:
    return run_agent(
        agent_name="orchestrator",
        system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
        task=user_prompt,
        tool_schemas=ORCHESTRATOR_TOOL_SCHEMAS,
        depth=0,
    )


def main() -> None:
    prompt = """Please complete this task step by step:

1. List all files in the workspace.
2. Read the content of hello.txt.
3. Create a new file named summary.txt containing a short summary of hello.txt.
4. Read summary.txt to verify its content.
5. Return a final answer describing what you completed."""
    print_color("=" * 20, Color.PINK)
    print_color(f"[User prompt]:\n{prompt}", Color.GREEN)

    result = run_agent(
        agent_name="orchestrator",
        system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
        task=prompt,
        tool_schemas=ORCHESTRATOR_TOOL_SCHEMAS,
        depth=0,
        run_id="resume-test-crash",
    )
    print_color("=========Final Result", Color.WHITE)
    print(result.result)


if __name__ == "__main__":
    main()
