import json


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


def print_color(text: str, color: str):

    # now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"{color}{text}{Color.RESET}")

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
