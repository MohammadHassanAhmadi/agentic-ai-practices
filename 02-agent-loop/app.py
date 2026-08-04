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

    RESET = "\033[0m"


def print_color(text: str, color: str):

    print(f"{color}{text}{Color.RESET}")


def count_words(input_text: str) -> str:

    return str(len(input_text.split()))


def to_uppercase(input_text: str) -> str:

    return input_text.upper()


def divide(a: int, b: int) -> str:

    if b == 0:
        raise ValueError("b cannot be zero, Zero Division Error")

    return str(a / b)


def get_env_value(variable_name: str) -> str:

    value = os.getenv(variable_name)

    if not value:
        raise RuntimeError(f"Missing required environment variable, {variable_name}")

    return value


model = get_env_value("AZURE_OPENAI_MODEL")

api_key = get_env_value("AZURE_OPENAI_API_KEY")

openai_endpoint = get_env_value("AZURE_OPENAI_ENDPOINT")


AGENT_SYSTEM_PROMPT = """


You are an AI agent that helps the user by using available tools.


Your responsibilities:


1. Understand the user's request.

2. Use the available tools only when needed.

3. Work one step at a time.

4. Call at most one tool per response.

5. After receiving a tool result, decide whether:


   * another tool is required, or

   * the task is complete and you can provide the final answer.

6. Respect the exact order requested by the user.

7. For chained operations, pass the previous tool result as the input to the next tool.

8. Do not reuse the original user input for the next chained tool unless the user explicitly requests it.

9. Never call the next tool before receiving the previous tool result.

10. Use tool results accurately.

11. Do not invent tool results.

12. Do not call a tool when required input is missing.

13. If the available tools cannot complete the request, explain that clearly.

14. When the task is complete, provide a concise final answer.

15. Do not describe your internal reasoning or create a JSON execution plan.

16. Never claim that a tool was executed unless you received its result.

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

DIVIDE_TOOL = {
    "type": "function",
    "name": "divide",
    "description": "divide two numbers(a/b)",
    "parameters": {
        "type": "object",
        "properties": {
            "a": {"type": "integer", "description": "the number to be divided"},
            "b": {"type": "integer", "description": "the number to divide by"},
        },
        "required": ["a", "b"],
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


TOOLS = [COUNT_WORDS_TOOL, TO_UPPERCASE_TOOL, DIVIDE_TOOL]


TOOLS_DICT = {
    "count_words": count_words,
    "to_uppercase": to_uppercase,
    "divide": divide,
}


client = OpenAI(api_key=api_key, base_url=openai_endpoint)


def log_file(msg: str):

    with open("output.txt", "a", encoding="utf-8") as file:
        file.write(msg)


def parse_json_string(json_string: str) -> dict:

    try:
        return json.loads(json_string)

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON string: {json_string}") from e


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

    print_color(f"message-History: {len(debug_messages)}", Color.GRAY)

    print_color(
        json.dumps(debug_messages, indent=2, default=str),
        Color.GRAY,
    )


def run_agent(user_input: str, messages: list[dict]):

    user_prompt = {"role": "user", "content": user_input}

    messages += [user_prompt]

    for round in range(5):
        print_message_history(messages)

        llm_resp = client.responses.create(
            model=model,
            instructions=AGENT_SYSTEM_PROMPT,
            input=messages,
            tools=TOOLS,
            parallel_tool_calls=False,
        )

        messages += llm_resp.output

        tool_was_called = False

        for item in llm_resp.output:
            print_color(f"llm_resp item.type: {item.type}", Color.YELLOW)

            if item.type != "function_call":
                continue

            result = call_tool(item.name, item.arguments)

            tool_was_called = True

            messages.append(
                {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": result,
                }
            )

        if not tool_was_called:
            msg = f"\n[Agent]: {llm_resp.output_text}\n\n"
            print_color(msg, Color.GREEN)
            log_file(msg)

            break

    else:
        print_color(
            "Agent stopped because it reached the maximum number of iterations.",
            Color.RED,
        )


messages = []

while True:
    user_input = input("[user]:\n")
    log_file(f"[user]:\n{user_input}")

    run_agent(user_input, messages)
