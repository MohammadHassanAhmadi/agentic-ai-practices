import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)


def get_env_var(variable_name: str) -> str:
    value = os.getenv(variable_name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {variable_name}")

    return value


# Create the sandbox workspace when the app starts.


openai_api_key = get_env_var("AZURE_OPENAI_API_KEY")
openai_endpoint = get_env_var("AZURE_OPENAI_ENDPOINT")
openai_model = get_env_var("AZURE_OPENAI_MODEL")

openai_client = OpenAI(api_key=openai_api_key, base_url=openai_endpoint)
