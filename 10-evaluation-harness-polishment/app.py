import json
import os
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

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


def run_agent(
    agent_name: str,
    system_prompt: str,
    task: str,
    tool_schemas: list,
    max_iterations: int = MAX_ATTEMPTS,
    depth: int = 0,
) -> AgentRun:

    history_messages: list[Any] = []
    tools_called: list[ToolCall] = []
    failed_delegations: set[tuple[str, str]] = set()

    try:
        append_to_history(history_messages, {"role": "user", "content": task})

        for agent_attempt in range(max_iterations):
            print_color(
                f" [{agent_name}] → (Attempt {agent_attempt + 1}/{max_iterations} | Depth {depth})",
                Color.GRAY,
            )

            llm_resp = client.responses.create(
                model=model,
                tools=tool_schemas,
                instructions=system_prompt,
                input=history_messages,
            )

            tool_was_called = False
            append_to_history(history_messages, llm_resp.output)

            for item in llm_resp.output:
                if item.type != "function_call":
                    continue

                if item.name == "call_sub_agent":
                    arguments = json.loads(item.arguments)
                    key = (arguments["agent_name"], arguments["task"])

                    if key in failed_delegations:
                        run = AgentRun(
                            status=RunStatus.FAILED,
                            error_code="DUPLICATE_DELEGATION",
                            result="This exact task already failed. Change the task or do it yourself.",
                        )
                    else:
                        run = call_sub_agent(
                            agent_name=arguments["agent_name"],
                            task=arguments["task"],
                            depth=depth,
                        )
                    result = to_result_envelope(run)

                    if run.status != RunStatus.SUCCESS:
                        failed_delegations.add(key)

                else:
                    result = tools.call_tool(item.name, item.arguments)

                tool_was_called = True

                tools_called.append(
                    ToolCall(name=item.name, arguments=json.loads(item.arguments))
                )
                append_to_history(
                    history_messages,
                    {
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": json.dumps(result),
                    },
                )
                print_color(f"[TOOL] result: {result}", Color.GRAY)

            if not tool_was_called:
                print_color(f"{agent_name} → {llm_resp.output_text}", Color.GREEN)
                return AgentRun(
                    status=RunStatus.SUCCESS,
                    result=llm_resp.output_text,
                    iterations=agent_attempt + 1,
                    tools_called=tools_called,
                )
        print_color(
            f"{agent_name} → Stopped working, max iterations reached",
            Color.RED,
        )
        return AgentRun(
            status=RunStatus.STOPPED,
            result="Max iterations reached",
            iterations=max_iterations,
            tools_called=tools_called,
        )
    except KeyboardInterrupt:
        print_color(f"\n{agent_name} → Exiting...", Color.RED)
        return AgentRun(
            status=RunStatus.STOPPED,
            result="Agent stopped by user",
            iterations=0,
            tools_called=tools_called,
        )

    except Exception as e:
        print_color(f"[{agent_name}] failed: {e!r}", Color.RED)
        return AgentRun(
            status=RunStatus.FAILED,
            error_code="AGENT_ERROR",
            result="The agent failed unexpectedly.",
            tools_called=tools_called,
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
    prompt = (
        "Ask the reader agent to delegate the reading of notes.txt to another "
        "reader agent. The reader must not read the file itself."
    )
    print_color(f"[User prompt]:\n{prompt}", Color.GREEN)

    result = run_agent(
        agent_name="orchestrator",
        system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
        task=prompt,
        tool_schemas=ORCHESTRATOR_TOOL_SCHEMAS,
        depth=0,
    )
    print(result.result)


if __name__ == "__main__":
    main()
