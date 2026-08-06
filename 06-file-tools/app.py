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

Keep your answers short."""


# for user_input in TEST_CASES:
history_messages = []
while True:
    print_color("[AGENT] How can I help you?", Color.PINK)
    user_input = input()
    # print_color(f"user input: {user_input}", Color.PURPLE)

    user_prompt = {"role": "user", "content": user_input}
    
    for agent_attempt in range(5):
        print_color(f"agent attempting:[{agent_attempt}]", Color.GRAY)
        llm_resp = client.responses.create(
            model=model,
            tools=tools.TOOLS,
            instructions=SYSTEM_PROMPT,
            input=user_prompt,
        )

        print_color(f"LLM response:{llm_resp.output_text}", Color.YELLOW)
        tool_was_called = False
    
        for item in llm_resp.output:
            if item.type != "function_call":
                continue

            result = tools.call_tool(item.name, item.arguments)
            tool_was_called = True

            if not tool_was_called:
                print_color(f"[AGENT]: {llm_resp.output_text}", Color.GREEN)
    print_color(
        "Agent stopped because it reached the maximum number of iterations.",
        Color.RED,
    )
