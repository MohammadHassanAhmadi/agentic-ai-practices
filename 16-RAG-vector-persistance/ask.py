import time
from pathlib import Path

import chromadb
from app import openai_api_key
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel, Field, SecretStr
from sentence_transformers import SentenceTransformer

from shared_tools.utiles import Color, print_color

DB_DIR = str(Path(__file__).parent / "chroma_db")
COLLECTION_NAME = "handbook"
TOP_K = 6
print(Path(DB_DIR).resolve())
embedder = SentenceTransformer("all-MiniLM-L6-v2")


class TestCase(BaseModel):
    id: int
    question: str
    expected_source: str | None
    expected_output_contains: list[str]
    why: str


class TestSuite(BaseModel):
    description: str
    cases: list[TestCase]


def get_collection():
    client = chromadb.PersistentClient(path=DB_DIR)
    return client.get_collection(name=COLLECTION_NAME)  # raises if missing


def search(collection, question: str, top_k: int = TOP_K) -> dict:
    """Embed the question and ask Chroma for the nearest chunks."""
    q_vec = embedder.encode([question]).tolist()
    return collection.query(
        query_embeddings=q_vec,
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )


class GroundedAnswer(BaseModel):
    answer: str = Field(
        description="the answer, or 'I don't know' if not in  the context"
    )
    used_sources: list[str] = Field(
        default_factory=list,
        description="source names actually used to build the answer; empty list if none",
    )


llm = AzureChatOpenAI(
    azure_endpoint="https://ai-foundry-cv-pilot.openai.azure.com/",
    api_key=SecretStr(openai_api_key),
    azure_deployment="gpt-5.4-nano",  # your deployment name in Azure
    api_version="2024-10-21",
)

llm_with_structured_model = llm.with_structured_output(GroundedAnswer)

SYSTEM_PROMPT = """You are a grounded question-answering assistant.

Rules:
1. Answer ONLY from the CONTEXT below. Never use your own knowledge.
2. If the CONTEXT does not contain the answer, reply exactly:
   "I don't know based on the provided documents."
   and return an empty used_sources list.
3. Do not soften, generalise, or add advice that is not in the CONTEXT.
   If the CONTEXT says something is forbidden, say it is forbidden.
4. In used_sources, list ONLY the sources you actually used to build the
   answer - not every source you were shown.

Each context line starts with its source in square brackets, like:
[deployment.md] Deployments to production are allowed...
"""

USER_PROMPT = """CONTEXT:
{context}

QUESTION:
{question}
"""


def build_context(vector_db_result: dict) -> tuple[str, list[str]]:
    documents = vector_db_result["documents"][0]
    metadatas = vector_db_result["metadatas"][0]
    distances = vector_db_result["distances"][0]

    sources = []
    lines = []
    for doc, meta, dist in zip(documents, metadatas, distances):
        source = meta["source"]
        lines.append(f"[{source}]  {doc}")
        sources.append(source)

        print_color(
            f"    retrieved {source}#{meta['chunk_index']} "
            f"(distance={dist:.3f}, similarity={1 - dist:.3f})",
            Color.GRAY,
        )
    unique_source = list(dict.fromkeys(sources))
    context = "\n\n".join(lines)

    return (context, unique_source)


def main():
    test_suit = TestSuite.model_validate_json(Path("inputs.json").read_text())

    collection = get_collection()
    print("Testing with ")
    for index, case in enumerate(test_suit.cases[6:]):
        print_color(f"    question[{index}] : {case.question}", Color.PINK)
        vector_db_results = search(collection=collection, question=case.question)

        (context, retrieved_sources) = build_context(vector_db_results)
        if index == 7:
            print_color(context, Color.YELLOW)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": USER_PROMPT.format(context=context, question=case.question),
            },
        ]
        llm_result = llm_with_structured_model.invoke(messages)

        print_color(f"    answer : {llm_result.answer}", Color.GREEN)
        print_color(f"    sources: {llm_result.used_sources}", Color.GREEN)

        # citation check: the model must not cite a file it was never shown
        invalid = [s for s in llm_result.used_sources if s not in retrieved_sources]
        if invalid:
            print_color(f"    INVALID SOURCES: {invalid}", Color.RED)

        print()

        time.sleep(2)


if __name__ == "__main__":
    main()
