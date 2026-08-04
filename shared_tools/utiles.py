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
