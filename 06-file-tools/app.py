# import os
# from pathlib import Path

# from dotenv import load_dotenv
# from openai import OpenAI

# load_dotenv(override=True)


# def get_env_var(variable_name: str) -> str:
#     value = os.getenv(variable_name)
#     if not value:
#         raise RuntimeError(f"Missing required environment variable: {variable_name}")

#     return value


# openai_api_key = get_env_var("AZURE_OPENAI_API_KEY")
# openai_endpoint = get_env_var("AZURE_OPENAI_ENDPOINT")
# model = get_env_var("AZURE_OPENAI_MODEL")

# client = OpenAI(api_key=openai_api_key, base_url=openai_endpoint)

# # create workspace on startup as sandbox
# Path("workspace").mkdir(exist_ok=True)


# def safe_path(path: str) -> Path:
#     """Resolve a user-supplied path and ensure it stays inside the workspace."""
#     workspace_path = Path("workspace").resolve()
#     full_path = (workspace_path / path).resolve()

#     if not full_path.is_relative_to(workspace_path):
#         raise ValueError(f"Access denied: path is outside the workspace: {path}")

#     return full_path


# def list_files() -> str:
#     """List all files in the workspace."""
#     workspace_path = Path("workspace").resolve()
#     files = [str(file) for file in workspace_path.iterdir() if file.is_file()]
#     return "\n".join(files)


# def read_file(path: str) -> str:
#     safe_path_ = safe_path(path)
#     content = Path(safe_path_).read_text()
#     return content


# def write_file(path: str, content: str) -> str:
#     try:
#         safe_file_path = safe_path(path)
#         safe_file_path.write_text(content)
#         return f"File written: {path} ({len(content)} characters)"
#     except Exception as e:
#         return f"Failure in writing file, file_path:{path}, exception-type:{type(e).__name__}, Message:{e}"

# def delete_path(path:str)-> str:
#     try:
#         safe_file_path = safe_path(path)
#         safe_file_path.unlink(missing_ok=True)
