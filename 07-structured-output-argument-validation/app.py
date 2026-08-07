import json
import os
from pathlib import Path

import tools
from dotenv import load_dotenv
from openai import OpenAI

from shared_tools.utiles import Color, print_color

load_dotenv(override=True)


def get_env_var(variable_name: str) -> str:
    value = os.getenv(variable_name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {variable_name}")

    return value


# create workspace on startup as sandbox
Path(tools.WORKSPACE_PATH).mkdir(exist_ok=True)

openai_api_key = get_env_var("AZURE_OPENAI_API_KEY")
openai_endpoint = get_env_var("AZURE_OPENAI_ENDPOINT")
model = get_env_var("AZURE_OPENAI_MODEL")

client = OpenAI(api_key=openai_api_key, base_url=openai_endpoint)
SYSTEM_PROMPT = """You are a file assistant. You work inside a workspace folder using the tools you are given.

Rules:
- Always use a tool to read or change files. Never guess a file's content.
- Paths are relative to the workspace root. You cannot access anything outside it.
- Writing to an existing file overwrites it. Read it first if you are unsure.
- Write and delete need user approval. If a tool says the user refused, tell the user clearly that nothing was changed. Do not retry.
- If a tool returns an error, explain it in plain words. Do not invent a result.
- Older messages may have been removed from your history. If you are not sure, say you do not know instead of guessing.

If a tool result contains approved: false, the user declined the action. Tell the user it was not done. Do not call the tool again with the same arguments.
Keep your answers short."""


def append_to_history_safely(history: list, items) -> list:

    if isinstance(items, list):
        history.extend(items)
    else:
        history.append(items)

    return history


# for user_input in TEST_CASES:
history_messages = []
while True:
    try:
        print_color("[AGENT] How can I help you?", Color.PINK)
        user_input = input()
        # print_color(f"user input: {user_input}", Color.PURPLE)

        user_prompt = {"role": "user", "content": user_input}
        history_messages.append(user_prompt)

        for agent_attempt in range(5):
            print_color(f"agent attempting:[{agent_attempt}]", Color.GRAY)
            llm_resp = client.responses.create(
                model=model,
                tools=tools.TOOLS,
                instructions=SYSTEM_PROMPT,
                input=history_messages,
            )

            tool_was_called = False
            append_to_history_safely(history_messages, llm_resp.output)
            for item in llm_resp.output:
                if item.type != "function_call":
                    continue

                result = tools.call_tool(item.name, item.arguments)

                tool_was_called = True
                history_messages.append(
                    {
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": json.dumps(result),
                    }
                )
                print_color(f"[TOOL]: {result}", Color.GRAY)

            if not tool_was_called:
                print_color(f"[AGENT]: {llm_resp.output_text}", Color.GREEN)
                break
        else:
            print_color(
                "Agent stopped because it reached the maximum number of iterations.",
                Color.RED,
            )
    except KeyboardInterrupt:
        print_color("\n[AGENT] Exiting...", Color.RED)
        break
