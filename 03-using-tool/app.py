import json
import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)


class Color:
    RED = "\033[31m"

    GREEN = "\033[32m"

    GRAY = "\033[90m"

    YELLOW = "\033[33m"

    BLUE = "\033[34m"

    PURPLE = "\033[35m"

    PINK = "\033[95m"

    RESET = "\033[0m"


def print_color(text: str, color: str):

    # now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"{color}{text}{Color.RESET}")

    with open("output.txt", "a", encoding="utf-8") as file:
        file.write(f"{text}\n")


def count_words(input_text: str) -> str:

    return str(len(input_text.split()))


def to_uppercase(input_text: str) -> str:

    return input_text.upper()


def get_env_value(variable_name: str) -> str:

    value = os.getenv(variable_name)

    if not value:
        raise RuntimeError(f"Missing required environment variable, {variable_name}")

    return value


model = get_env_value("AZURE_OPENAI_MODEL")

api_key = get_env_value("AZURE_OPENAI_API_KEY")

openai_endpoint = get_env_value("AZURE_OPENAI_ENDPOINT")


AGENT_SYSTEM_PROMPT = """
You are an AI agent that completes user requests using the available tools.

Rules:

1. Understand the request and follow the requested order.
2. Call tools only when needed and only when all required inputs are available.
3. Use tool results accurately. Never invent results or claim a tool ran without receiving its output.
4. After each tool result, either call the next required tool or provide the final answer.
5. For chained operations, pass each tool’s output to the next tool instead of reusing the original input.
6. If the tools cannot complete the request, explain the limitation clearly.
7. When finished, provide a concise final answer.
8.older messages may have been removed; if you don't see something, say you don't know instead of guessing.

Do not reveal internal reasoning or generate an execution plan.

"""


COUNT_WORDS_TOOL = {
    "type": "function",
    "name": "count_words",
    "description": "Count the number of words in a piece of text.",
    "parameters": {
        "type": "object",
        "properties": {
            "input_text": {
                "type": "string",
                "description": "The text whose words should be counted.",
            }
        },
        "required": ["input_text"],
        "additionalProperties": False,
    },
}


TO_UPPERCASE_TOOL = {
    "type": "function",
    "name": "to_uppercase",
    "description": "Convert a piece of text to uppercase.",
    "parameters": {
        "type": "object",
        "properties": {
            "input_text": {
                "type": "string",
                "description": "The text to convert to uppercase.",
            }
        },
        "required": ["input_text"],
        "additionalProperties": False,
    },
}


TOOLS = [COUNT_WORDS_TOOL, TO_UPPERCASE_TOOL]

TOOLS_DICT = {"count_words": count_words, "to_uppercase": to_uppercase}


client = OpenAI(api_key=api_key, base_url=openai_endpoint)


def parse_json_string(json_string: str) -> dict:

    try:
        return json.loads(json_string)

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON string: {json_string}") from e


HISTORY_LIMIT_SIZE = 6


def get_readable_json(data) -> str:

    dt = data

    if hasattr(dt, "model_dump"):
        dt = dt.model_dump()

    return json.dumps(dt, indent=2, default=str)


def summarize_conversation(input_message):
    SUMMERIZE_PROMPT = """Summarize the conversation so far in a concise manner, keeping all relevant information for future context.
            summarize this conversation into a few short facts"""
    llm_resp = client.responses.create(
        model=model,
        instructions=SUMMERIZE_PROMPT,
        input=input_message,
    )

    return {"role": "assistant", "content": llm_resp.output_text}


def remove_oldest_messages(history: list, limit_size=HISTORY_LIMIT_SIZE) -> list:
    removed = []
    while len(history) > limit_size:
        print_color("History limit exceeded. Removing:\n", Color.RED)
        removed.append(history.pop(0))
        print(f"-----removed type: {type(removed[-1])}")

        if hasattr(removed[-1], "call_id"):
            print_color(
                f"---a function call with call_id: {removed[-1].call_id} is being removed from history.",
                Color.PINK,
            )

            removed.append(
                history.pop(0)
            )  # Remove the corresponding function_call_output

        print_color(f"{get_readable_json(removed)}", Color.GRAY)

    if len(removed) > 0:
        summarization = summarize_conversation(removed)
        history.insert(0, summarization)
    else:
        print_color("No messages removed.", Color.GREEN)
    return history


def append_to_history_safely(history: list, items) -> list:

    if isinstance(items, list):
        history.extend(items)
    else:
        history.append(items)
    remove_oldest_messages(history)
    print_message_history(history)
    return history


def call_tool(tool_name: str, tool_arg_str: str) -> Any:

    try:
        tool_function = TOOLS_DICT.get(tool_name)

        if tool_function is None:
            raise ValueError(f"unknown tool: {tool_name}")

        arguments = parse_json_string(tool_arg_str)

        result = tool_function(**arguments)

        arguments_text = ", ".join(
            f"{key}={value!r}" for key, value in arguments.items()
        )

        print_color(
            f"tool_called: {tool_name}({arguments_text}) => {result}", Color.YELLOW
        )

    except Exception as e:
        result = f"Error: {type(e).__name__}: {e}"

        print_color(f"there was an error calling the tool:{result}", Color.RED)

    return result


def print_message_history(messages: list[dict]):

    debug_messages = [
        message.model_dump() if hasattr(message, "model_dump") else message
        for message in messages
    ]

    print_color(f"message-History: {len(debug_messages)}", Color.PURPLE)

    print_color(
        json.dumps(debug_messages, indent=2, default=str),
        Color.YELLOW,
    )


def run_agent_loop(user_input: str, history_messages: list) -> str | None:

    print_color(f"message count: {len(history_messages)}", Color.PURPLE)

    print_color(f"user input: {user_input}", Color.RED)

    user_prompt = {"role": "user", "content": user_input}

    append_to_history_safely(history_messages, user_prompt)

    for _ in range(5):
        llm_resp = client.responses.create(
            model=model,
            instructions=AGENT_SYSTEM_PROMPT,
            input=history_messages,
            tools=TOOLS,
            parallel_tool_calls=True,
        )

        append_to_history_safely(history_messages, llm_resp.output)

        tool_was_called = False

        for item in llm_resp.output:
            if item.type != "function_call":
                continue

            result = call_tool(item.name, item.arguments)

            tool_was_called = True

            append_to_history_safely(
                history_messages,
                {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": result,
                },
            )

        if not tool_was_called:
            print_color(f"final answer: {llm_resp.output_text}", Color.GREEN)

            return llm_resp.output_text

    print_color(
        "Agent stopped because it reached the maximum number of iterations.",
        Color.RED,
    )

    return "Agent stopped because it reached the maximum number of iterations."
