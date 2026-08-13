from enum import Enum
from pathlib import Path

from shared_tools import utiles

WORKSPACE_PATH = (Path(__file__).parent / "workspace").resolve()
MAX_BYTES = 8192


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
    files = [
        {"name": file.name, "size": file.stat().st_size}
        for file in WORKSPACE_PATH.iterdir()
        if file.is_file()
    ]
    if not files:
        return {
            "files": [],
            "file_count": 0,
            "message": "No files found in the workspace.",
        }

    return {"files": files, "file_count": len(files)}


def search_files(query: str, max_results: int = 0) -> dict:
    """Search every text file in the workspace for lines containing `query`."""
    if not isinstance(query, str) or not query:
        raise ToolError(
            code=ErrorCode.INVALID_ARGUMENTS,
            message="Invalid query value. Query must be a non-empty string.",
        )

    if not isinstance(max_results, int) or max_results < 0:
        raise ToolError(
            code=ErrorCode.INVALID_ARGUMENTS,
            message=f"Invalid max_results value: {max_results}. Must be a non-negative integer.",
        )

    matches = []
    truncated = False

    for file in WORKSPACE_PATH.rglob("*"):
        if not file.is_file():
            continue

        try:
            lines = file.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue

        for line_number, line in enumerate(lines, start=1):
            if query.lower() in line.lower():
                matches.append(
                    {
                        "file": file.relative_to(WORKSPACE_PATH).as_posix(),
                        "line": line_number,
                        "text": line,
                    }
                )
                if max_results > 0 and len(matches) >= max_results:
                    truncated = True
                    return {
                        "matches": matches,
                        "match_count": len(matches),
                        "truncated": truncated,
                    }

    return {
        "matches": matches,
        "match_count": len(matches),
        "truncated": truncated,
    }


def read_file(path: str) -> dict:
    safe_file_path = safe_path(path)
    try:
        total_bytes = safe_file_path.stat().st_size

        if total_bytes > MAX_BYTES:
            with open(safe_file_path, "rb") as file:
                chunk = file.read(MAX_BYTES)
            content = chunk.decode("utf-8", errors="ignore")
            return {
                "content": content,
                "truncated": True,
                "returned_bytes": MAX_BYTES,
                "total_bytes": total_bytes,
            }

        content = safe_file_path.read_text(encoding="utf-8")
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

LIST_FILES_SCHEMA = {
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

SEARCH_FILES_SCHEMA = {
    "type": "function",
    "name": "search_files",
    "strict": True,
    "description": "Searches every file in the workspace for lines containing the query string.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The text to search for.",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of matches to return. Set to 0 to return all matches.",
            },
        },
        "required": ["query", "max_results"],
        "additionalProperties": False,
    },
}

READ_FILE_SCHEMA = {
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

WRITE_FILE_SCHEMA = {
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

DELETE_FILE_SCHEMA = {
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

TOOL_SCHEMA_LIST = [
    LIST_FILES_SCHEMA,
    READ_FILE_SCHEMA,
    WRITE_FILE_SCHEMA,
    DELETE_FILE_SCHEMA,
    SEARCH_FILES_SCHEMA,
]

TOOL_FUNCTIONS = {
    "list_files": list_files,
    "read_file": read_file,
    "write_file": write_file,
    "delete_file": delete_file,
    "search_files": search_files,
}

NEEDS_APPROVAL_TOOLS = {"write_file", "delete_file"}
AUTO_APPROVE = True


class ErrorCode(str, Enum):
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    PATH_OUTSIDE_WORKSPACE = "PATH_OUTSIDE_WORKSPACE"
    UNKNOWN_TOOLS = "UNKNOWN_TOOLS"
    USER_DENIED = "USER_DENIED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    INVALID_ARGUMENTS = "INVALID_ARGUMENTS"
    DELEGATION_NOT_ALLOWED = "DELEGATION_NOT_ALLOWED"
    DUPLICATE_DELEGATION = "DUPLICATE_DELEGATION"


class ToolError(Exception):
    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


def call_tool(tool_name: str, arg_json_str: str) -> dict:
    try:
        tool_function = TOOL_FUNCTIONS.get(tool_name)
        if tool_function is None:
            raise ToolError(
                code=ErrorCode.UNKNOWN_TOOLS,
                message=f"unknown tool name: {tool_name!r}",
            )

        arguments = utiles.parse_json_string(arg_json_str)

        if not AUTO_APPROVE and tool_name in NEEDS_APPROVAL_TOOLS:
            user_answer = input(
                f"Approve {tool_name} with {arguments}? Type yes or no: "
            )
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
    except Exception as e:
        utiles.print_color(f"[INTERNAL] {tool_name} failed: {e!r}", utiles.Color.RED)
        return {
            "ok": False,
            "error": {
                "code": ErrorCode.INTERNAL_ERROR,
                "message": "The tool failed unexpectedly.",
            },
        }
