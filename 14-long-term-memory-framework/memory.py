import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from openai import OpenAI
from pydantic import BaseModel

MEMORY_FILE = Path("memories.json")

MEMORY_EXTRACTION_PROMPT = """
Extract only durable and useful long-term information about the user.

Store:
- Stable personal facts
- Preferences
- Long-term goals
- Important constraints

Do not store:
- Questions
- Temporary information
- Uncertain assumptions
- Sensitive information
- Conversation details

Write each memory as a short standalone fact.
Return an empty list when there is nothing worth remembering.
"""


class MemoryExtraction(BaseModel):
    memories: list[str]


@dataclass
class Memory:
    id: str
    user_id: str
    content: str
    created_at: str


def extract_memories(client: OpenAI, model: str, user_input: str) -> list[str]:
    response = client.responses.parse(
        model=model,
        instructions=MEMORY_EXTRACTION_PROMPT,
        input=[
            {
                "role": "user",
                "content": user_input,
            },
        ],
        text_format=MemoryExtraction,
    )

    if response.output_parsed is None:
        return []

    return response.output_parsed.memories


def save_memory(user_id: str, content: str) -> Memory:
    memories = []

    if MEMORY_FILE.exists():
        memories = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))

    normalized_content = content.strip().lower()

    for item in memories:
        if item["user_id"] == user_id:
            normalized_memory_content = item["content"].strip().lower()
            if normalized_content == normalized_memory_content:
                return Memory(**item)

    new_memory = Memory(
        id=str(uuid4()),
        content=content,
        user_id=user_id,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    memories.append(asdict(new_memory))

    MEMORY_FILE.write_text(
        json.dumps(memories, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return new_memory


def load_memories(user_id: str) -> list[Memory]:
    if not MEMORY_FILE.exists():
        return []

    user_memories = []
    memories = json.loads(MEMORY_FILE.read_text("utf-8"))

    for item in memories:
        if item["user_id"] == user_id:
            user_memories.append(Memory(**item))

    return user_memories


def update_memory(user_id: str, memory_id: str, new_content: str) -> Memory | None:
    if not MEMORY_FILE.exists():
        return None

    stored_memories = json.loads(MEMORY_FILE.read_text("utf-8"))

    for memory in stored_memories:
        if memory["user_id"] == user_id and memory["id"] == memory_id:
            memory["content"] = new_content.strip()
            MEMORY_FILE.write_text(
                json.dumps(stored_memories, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return Memory(**memory)

    return None


def delete_memory(user_id: str, memory_id: str) -> bool:
    if not MEMORY_FILE.exists():
        return False

    stored_memories = json.loads(MEMORY_FILE.read_text("utf-8"))

    remaining_memories = []
    memory_found = False

    for item in stored_memories:
        if not memory_found and item["user_id"] == user_id and item["id"] == memory_id:
            memory_found = True
            continue

        remaining_memories.append(item)

    if not memory_found:
        return False

    MEMORY_FILE.write_text(
        json.dumps(remaining_memories, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return True


def build_memory_context(memories: list[Memory]) -> str:
    if not memories:
        return "No long-term memory is available for this user"

    lines = ["Known information about the user:"]

    for memory in memories:
        lines.append(f"- {memory.content}")

    return "\n".join(lines)


################################


if __name__ == "__main__":
    memories = load_memories("hassan")
    target_memory = None

    for memory in memories:
        if memory.content.lower() == "user prefers light mode.":
            target_memory = memory
            break

    if target_memory is None:
        raise RuntimeError("Test memory was not found")

    before_count = len(memories)

    first_delete = delete_memory(
        user_id="hassan",
        memory_id=target_memory.id,
    )

    second_delete = delete_memory(
        user_id="hassan",
        memory_id=target_memory.id,
    )

    after_count = len(load_memories("hassan"))

    print(f"First delete: {first_delete}")
    print(f"Second delete: {second_delete}")
    print(f"Count decreased: {after_count == before_count - 1}")
