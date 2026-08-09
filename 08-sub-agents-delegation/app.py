import json
import os
from dataclasses import dataclass, field
from enum import StrEnum

import tools
from dotenv import load_dotenv
from openai import OpenAI
from system_prompts import ORCHESTRATOR_SYSTEM_PROMPT, READER_SYSTEM_PROMPT

from shared_tools.utiles import Color, print_color

load_dotenv(override=True)


def get_env_var(variable_name: str) -> str:
    value = os.getenv(variable_name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {variable_name}")

    return value


# create workspace on startup as sandbox
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
class AgentRun:
    status: RunStatus = RunStatus.PENDING
    result: str = ""
    error_code: str | None = None
    iterations: int = 0
    tools_called: list[str] = field(default_factory=list)


def append_to_history_safely(history: list, items) -> list:
    if isinstance(items, list):
        history.extend(items)
    else:
        history.append(items)

    return history


MAX_TRY_ATTEMPT = 5
MAX_DEPTH = 1
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


def call_sub_agent(agent_name, task, depth):

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
        max_iterations=MAX_TRY_ATTEMPT,  # for now the same as main agent, but could be different
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


def to_result_envelop(run: AgentRun) -> dict:

    if run.status == RunStatus.SUCCESS:
        return {
            "ok": True,
            "data": {
                "status": run.status.value,
                "result": run.result,
                "iterations": run.iterations,
                "tools_called": run.tools_called,
            },
        }
    else:
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
    max_iterations: int = MAX_TRY_ATTEMPT,
    depth: int = 0,
) -> AgentRun:

    history_messages = []
    tools_called = []
    failed_delegations = set()

    try:
        user_prompt = {"role": "user", "content": task}

        append_to_history_safely(history_messages, user_prompt)

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
            append_to_history_safely(history_messages, llm_resp.output)
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
                    result = to_result_envelop(run)

                    if run.status != RunStatus.SUCCESS:
                        failed_delegations.add(key)

                else:
                    result = tools.call_tool(item.name, item.arguments)

                tool_was_called = True
                tools_called.append(item.name)
                append_to_history_safely(
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
            iterations=MAX_TRY_ATTEMPT,
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


# while True: # for when you want real app

for prompt in [
    "Ask the reader agent to delegate the reading of notes.txt to another reader agent. The reader must not read the file itself."
]:
    # print_color("How can I help?", Color.GREEN)
    print_color(f"[User prompt]:\n{prompt}", Color.GREEN)
    # prompt = input("Enter prompt:\n")
    main_task_result = run_agent(
        agent_name="Orchestrator",
        system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
        task=prompt,
        tool_schemas=ORCHESTRATOR_TOOL_SCHEMAS,
        max_iterations=MAX_TRY_ATTEMPT,
        depth=0,
    )

    print(main_task_result.result)
