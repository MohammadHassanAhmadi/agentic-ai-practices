from enum import Enum
from pathlib import Path

from shared_tools import utiles

WORKSPACE_PATH = (Path(__file__).parent / "workspace").resolve()
# resolve is getFullPath


def safe_path(path: str) -> Path:
    """Resolve a user-supplied path and ensure it stays inside the workspace."""
    full_path = (WORKSPACE_PATH / path).resolve()

    if not full_path.is_relative_to(WORKSPACE_PATH):
        raise ToolError(
            code=ErrorCode.PATH_OUTSIDE_WORKSPACE,
            message=f"Access denied: path is outside the workspace: {path}",
        )

    return full_path


def list_files() -> dict:
    """List all files in the workspace."""
    workspace_path = WORKSPACE_PATH
    files = [
        {"name": file.name, "size": file.stat().st_size}
        for file in workspace_path.iterdir()
        if file.is_file()
    ]
    if len(files) == 0:
        return {
            "files": [],
            "file_count": 0,
            "message": "No files found in the workspace.",
        }

    return {"files": files, "file_count": len(files)}


MAX_BYTES = 8192


def read_file(path: str) -> dict:
    file_safe_path = safe_path(path)
    try:
        total_bytes = file_safe_path.stat().st_size

        if total_bytes > MAX_BYTES:
            with open(file_safe_path, "rb") as f:
                chunk = f.read(MAX_BYTES)
            content = chunk.decode("utf-8", errors="ignore")
            return {
                "content": content,
                "truncated": True,
                "returned_bytes": MAX_BYTES,
                "total_bytes": total_bytes,
            }

        content = file_safe_path.read_text(encoding="utf-8")
        return {
            "content": content,
            "truncated": False,
            "returned_bytes": total_bytes,
            "total_bytes": total_bytes,
        }
    except FileNotFoundError as e:
        raise ToolError(ErrorCode.FILE_NOT_FOUND, f"File not found: {path}") from e


def write_file(path: str, content: str) -> dict:
    safe_file_path = safe_path(path)
    safe_file_path.write_text(content, encoding="utf-8")
    return {
        "total_bytes": len(content.encode("utf-8")),
        "message": f"File written successfully: {path}",
    }


def delete_file(path: str) -> dict:
    safe_file_path = safe_path(path)
    safe_file_path.unlink()
    return {
        "filename": safe_file_path.name,
        "message": f"File deleted successfully: {path}",
    }


PATH_DESCRIPTION = (
    "Path to the file, relative to the workspace root. "
    "Example: 'notes.txt' or 'docs/readme.md'. "
    "Paths outside the workspace are not allowed."
)

LIST_FILES_TOOL = {
    "type": "function",
    "name": "list_files",
    "strict": True,
    "description": "Returns a list of files in the workspace, including file names and sizes.",
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
    "description": "Reads and returns the contents of a workspace file, truncating output to 8 KB for larger files.",
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
    "description": "Writes content to a workspace file, creating it or overwriting it.",
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
    "description": "Deletes a workspace file. This action cannot be undone.",
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


class ErrorCode(str, Enum):
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    PATH_OUTSIDE_WORKSPACE = "PATH_OUTSIDE_WORKSPACE"
    UNKNOWN_TOOLS = "UNKNOWN_TOOLS"
    USER_DENIED = "USER_DENIED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ToolError(Exception):
    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


def call_tool(tool_name: str, arg_json_str: str) -> dict:
    try:
        tool_function = TOOLS_DICT.get(tool_name)
        if tool_function is None:
            raise ToolError(
                code=ErrorCode.UNKNOWN_TOOLS,
                message=f"unknown tool name: {tool_name!r}",
            )

        arguments = utiles.parse_json_string(arg_json_str)

        if tool_name in NEEDS_APPROVAL:
            user_answer = input(f"Approve {tool_name} on {arguments}[yes/no]?")
            if user_answer.strip().lower() != "yes":
                return {
                    "ok": True,
                    "data": {"approved": False, "code": ErrorCode.USER_DENIED},
                }

        result = tool_function(**arguments)
        arguments_text = ", ".join(
            f"{key}={value!r}" for key, value in arguments.items()
        )
        utiles.print_color(
            f"tool_called: {tool_name}({arguments_text}) => {result}",
            utiles.Color.YELLOW,
        )
        return {"ok": True, "data": result}

    except ToolError as e:
        return {"ok": False, "error": {"code": e.code, "message": str(e)}}
    except FileNotFoundError as e:
        return {
            "ok": False,
            "error": {"code": ErrorCode.FILE_NOT_FOUND, "message": str(e)},
        }
    except Exception:
        return {
            "ok": False,
            "error": {
                "code": ErrorCode.INTERNAL_ERROR,
                "message": "The tool failed unexpectedly.",
            },
        }
