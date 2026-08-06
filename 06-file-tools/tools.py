from pathlib import Path
from typing import Any

from shared_tools import utiles

WORKSPACE_PATH = (Path(__file__).parent / "workspace").resolve()
# resolve is getFullPath


def safe_path(path: str) -> Path:
    """Resolve a user-supplied path and ensure it stays inside the workspace."""
    workspace_path = Path("workspace").resolve()
    full_path = (workspace_path / path).resolve()

    if not full_path.is_relative_to(workspace_path):
        raise ValueError(f"Access denied: path is outside the workspace: {path}")

    return full_path


def list_files() -> str:
    """List all files in the workspace."""
    workspace_path = Path("workspace").resolve()
    files = [file.name for file in workspace_path.iterdir() if file.is_file()]
    if len(files) == 0:
        return "Workspace is empty"
    return "\n".join(files)


def read_file(path: str) -> str:
    content = Path(safe_path(path)).read_text()
    return content


def write_file(path: str, content: str) -> str:
    safe_file_path = safe_path(path)
    safe_file_path.write_text(content)
    return f"File written: {path} ({len(content)} characters)"


def delete_file(path: str) -> str:
    safe_file_path = safe_path(path)
    safe_file_path.unlink()
    return f"File deleted: {path}"


PATH_DESCRIPTION = (
    "Path to the file, relative to the workspace root. "
    "Example: 'notes.txt' or 'docs/readme.md'. "
    "Paths outside the workspace are not allowed."
)

LIST_FILES_TOOL = {
    "type": "function",
    "name": "list_files",
    "strict": True,
    "description": "Lists the files in the workspace.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
}

READ_FILE_TOOL = {
    "type": "function",
    "name": "read_file",
    "strict": True,
    "description": "Reads and returns the content of a file.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": PATH_DESCRIPTION,
            }
        },
        "required": ["path"],
        "additionalProperties": False,
    },
}

WRITE_FILE_TOOL = {
    "type": "function",
    "name": "write_file",
    "strict": True,
    "description": "Writes content to a file, creating it or overwriting it.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": PATH_DESCRIPTION,
            },
            "content": {
                "type": "string",
                "description": "The full content to write to the file.",
            },
        },
        "required": ["path", "content"],
        "additionalProperties": False,
    },
}

DELETE_FILE_TOOL = {
    "type": "function",
    "name": "delete_file",
    "strict": True,
    "description": "Deletes a file. This cannot be undone.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": PATH_DESCRIPTION,
            }
        },
        "required": ["path"],
        "additionalProperties": False,
    },
}

TOOLS = [
    LIST_FILES_TOOL,
    READ_FILE_TOOL,
    WRITE_FILE_TOOL,
    DELETE_FILE_TOOL,
]

TOOLS_DICT = {
    "list_files": list_files,
    "read_file": read_file,
    "write_file": write_file,
    "delete_file": delete_file,
}

NEEDS_APPROVAL = {"write_file", "delete_file"}


def call_tool(tool_name: str, arg_json_str: str) -> Any:
    try:
        tool_function = TOOLS_DICT.get(tool_name)
        if tool_function is None:
            raise ValueError(f"unknown tool: {tool_name}")

        arguments = utiles.parse_json_string(arg_json_str)
        if tool_name in NEEDS_APPROVAL:
            user_answer = input(f"Approve {tool_name} on {arguments}[yes/no]?")
            if user_answer.strip().lower() != "yes":
                return f"User denied to {tool_name} on {arguments}"

        result = tool_function(**arguments)
        arguments_text = ", ".join(
            f"{key}={value!r}" for key, value in arguments.items()
        )
        utiles.print_color(
            f"tool_called: {tool_name}({arguments_text}) => {result}",
            utiles.Color.YELLOW,
        )
        return result
    except Exception as e:
        result = f"Error: {type(e).__name__}: {e}"
        utiles.print_color(
            f"there was an error calling the tool:{result}", utiles.Color.RED
        )
        return result
