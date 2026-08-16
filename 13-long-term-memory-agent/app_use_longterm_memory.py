from app import client, openai_model
from memory import build_memory_context, load_memories

from shared_tools.utiles import Color, print_color

if __name__ == "__main__":
    memory_context = build_memory_context(load_memories(user_id="hassan"))

    instructions = f"""
    You are a helpful assistant.

    Use the following long-term memory when it is relevant.
    Do not mention the memory system unless the user asks about it.
    {memory_context}
    """

    response = client.responses.create(
        model=openai_model,
        instructions=instructions,
        input="What programming language should you use in examples for me? answer me in json format",
    )

    print_color(f"[AGENT]:\n{response.output_text}", Color.GREEN)
