import json
from datetime import datetime


import sys


class Color:
    RED = "\033[31m"

    GREEN = "\033[32m"

    GRAY = "\033[90m"

    YELLOW = "\033[33m"

    BLUE = "\033[34m"

    PURPLE = "\033[35m"

    PINK = "\033[95m"

    RESET = "\033[0m"

    WHITE = "\033[37m"


def configure_utf8_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def format_console_message(text: str) -> str:
    """Add a compact timestamp and a useful category to console output."""

    message = str(text).strip("\n")
    if not message:
        return f"[{datetime.now():%H:%M:%S}]"

    label = ""
    if not message.startswith("["):
        label_by_text = (
            ("tool_called:", "TOOL"),
            ("there was an error", "ERROR"),
            ("failed", "ERROR"),
            ("message-History:", "STATE"),
            ("message count:", "STATE"),
            ("llm_resp", "MODEL"),
            ("thinking", "MODEL"),
            ("state saved", "MEMORY"),
            ("Loading state", "MEMORY"),
            ("syncing state", "MEMORY"),
            ("sync completed", "MEMORY"),
            ("Running task", "RUN"),
            ("final answer", "AGENT"),
            ("Final Result", "AGENT"),
        )
        for marker, candidate in label_by_text:
            if marker.lower() in message.lower():
                label = f" [{candidate}]"
                break

    prefix = f"[{datetime.now():%H:%M:%S}]{label} "
    lines = message.splitlines()
    return prefix + (f"\n{' ' * len(prefix)}".join(lines))


def print_color(text: str, color: str):

    formatted_text = format_console_message(text)
    print(f"{color}{formatted_text}{Color.RESET}")

    with open("output.txt", "a", encoding="utf-8") as file:
        file.write(f"{text}\n")


def parse_json_string(json_string: str) -> dict:

    try:
        return json.loads(json_string)

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON string: {json_string}") from e


def to_pretty_json(data) -> str:

    dt = data
    if hasattr(dt, "model_dump"):
        dt = dt.model_dump()

    return json.dumps(dt, indent=2, default=str)
