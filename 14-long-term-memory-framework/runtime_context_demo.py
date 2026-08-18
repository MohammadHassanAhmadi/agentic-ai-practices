from dataclasses import dataclass
from uuid import uuid4

from app import openai_api_key, openai_model
from langchain_openai import AzureChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from langgraph.store.base import BaseStore
from langgraph.store.sqlite import SqliteStore
from pydantic import BaseModel, Field
from typing_extensions import NotRequired, TypedDict


class AgentState(TypedDict):
    message: str
    memories: NotRequired[list[str]]
    memory_id: NotRequired[str]
    memory_saved: NotRequired[bool]
    answer: NotRequired[str]
    memory_candidate: NotRequired[str | None]


class MemoryDecision(BaseModel):
    should_save: bool = Field(
        description="whether this message contains a durable fact or preference"
    )

    content: str | None = Field(
        default=None,
        description="A short normalized memory, or null when nothing should be saved",
    )


llm = AzureChatOpenAI(
    azure_endpoint="https://ai-foundry-cv-pilot.openai.azure.com/",
    api_key=openai_api_key,
    azure_deployment=openai_model,
    api_version="2024-10-21",
)

memory_extractor_llm = llm.with_structured_output(MemoryDecision)


@dataclass
class Context:
    user_id: str


def extract_memory_candidate(state: AgentState) -> dict:
    decision = memory_extractor_llm.invoke(f"""
    Extract a memory only when the user message contains a stable useful fact or preference.
    
    Do not save:
    - questions
    - temporary requests
    - greetings
    - sensitive information
    
    user message:{state["message"]}
""")

    return {"memory_candidate": decision.content if decision.should_save else None}


def answer_with_memory(state: AgentState) -> dict:
    memories = state.get("memories", [])

    memory_context = "\n".join(f"-{memory}" for memory in memories)

    prompt = f"""
    You are a helpful assistant.
    
    Know facts about this user:
    {memory_context or "- No store memories"}
    
    User question:
    {state["message"]}
    
    Answer using the known facts only when they are relevant.
    
    """

    response = llm.invoke(prompt)

    return {"answer": response.content}


def normalize_text(text: str) -> str:
    return text.strip().strip(".").lower()


def save_memory(state: AgentState, runtime: Runtime[Context]) -> dict:
    store = runtime.store
    if store is None:
        raise RuntimeError("Store is not configured")

    namespace = (runtime.context.user_id, "memories")

    content = state.get("memory_candidate")
    if content is None:
        return {"memory_saved": False}

    # Exact duplicate detection
    for item in store.search(namespace):
        stored_content = item.value.get("content") or ""
        if normalize_text(stored_content) == normalize_text(content):
            return {"memory_id": item.key, "memory_saved": False}

    memory_id = str(uuid4())

    store.put(namespace=namespace, key=memory_id, value={"content": content})

    return {"memory_id": memory_id, "memory_saved": True}


def load_user_memories(state: AgentState, runtime: Runtime[Context]) -> dict:
    store = runtime.store

    if store is None:
        raise RuntimeError("Store is not configured")

    namespace = (runtime.context.user_id, "memories")

    stored_items = store.search(namespace)

    memories = []

    for item in stored_items:
        memories.append(item.value["content"])

    return {"memories": memories}


def update_memory(
    store: BaseStore, user_id: str, memory_id: str, new_content: str
) -> None:

    namespace = (user_id, "memories")

    existing_memory = store.get(namespace=namespace, key=memory_id)
    if existing_memory is None:
        raise ValueError("Memory not found")

    store.put(namespace=namespace, key=memory_id, value={"content": new_content})


def delete_memory(store: BaseStore, user_id: str, memory_id: str) -> None:

    namespace = (user_id, "memories")

    existing_memory = store.get(namespace=namespace, key=memory_id)
    if existing_memory is None:
        raise ValueError("Memory not found")

    store.delete(namespace=namespace, key=memory_id)


def should_save(state: AgentState) -> str:
    memory_candidate = state.get("memory_candidate")
    if memory_candidate is not None:
        return "save_memory"
    return END


def build_graph(store: BaseStore):
    builder = StateGraph(AgentState, context_schema=Context)

    builder.add_node("load_user_memories", load_user_memories)
    builder.add_node("answer_with_memory", answer_with_memory)
    builder.add_node("extract_memory_candidate", extract_memory_candidate)
    builder.add_node("save_memory", save_memory)

    builder.add_edge(START, "load_user_memories")
    builder.add_edge("load_user_memories", "answer_with_memory")
    builder.add_edge("answer_with_memory", "extract_memory_candidate")
    builder.add_conditional_edges("extract_memory_candidate", should_save)
    builder.add_edge("save_memory", END)
    return builder.compile(store=store)


def main() -> None:
    with SqliteStore.from_conn_string("memories.db") as store:
        store.setup()
        graph = build_graph(store)

        # tests = [
        #     "I prefer dark roast coffee",  # باید ذخیره بشه
        #     "what time is it?",  # نباید ذخیره بشه
        #     "I prefer dark roast coffee",  # تکراری → ذخیره نشه
        #     "what kind of coffee do I like?",  # باید از حافظه جواب بده
        # ]

        # for message in tests:
        #     result = graph.invoke(
        #         {"message": message},
        #         context=Context(user_id="hassan"),
        #     )
        #     print(f"\n>>> {message}")
        #     print(f"    saved   : {result.get('memory_saved')}")
        #     print(f"    answer  : {result['answer']}")

        print("\n--- stored memories for hassan ---")
        for item in store.search(("hassan", "memories")):
            print(f"   [{item.key[:8]}] {item.value['content']}")

        print("\n--- stored memories for ali ---")
        for item in store.search(("ali", "memories")):
            print(f"   [{item.key[:8]}] {item.value['content']}")
        # print("\n--- user isolation ---")
        # graph.invoke(
        #     {"message": "I am allergic to peanuts"},
        #     context=Context(user_id="ali"),
        # )
        # result = graph.invoke(
        #     {"message": "am I allergic to anything?"},
        #     context=Context(user_id="hassan"),
        # )

        # print(f"  hassan sees: {result['answer']}")


if __name__ == "__main__":
    main()
