import time
from pathlib import Path

from app import openai_api_key
from db import get_connection
from ingest import embed
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel, Field, SecretStr

from shared_tools.utiles import Color, print_color

TOP_K = 4


class GroundedAnswer(BaseModel):
    answer: str = Field(
        description="the answer, or 'I don't know' if not in  the context"
    )
    used_sources: list[str] = Field(
        default_factory=list,
        description="source names actually used to build the answer; empty list if none",
    )


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


class TestCase(BaseModel):
    id: int
    question: str
    expected_source: str | None
    expected_output_contains: list[str]
    why: str


class TestSuite(BaseModel):
    description: str
    cases: list[TestCase]


llm = AzureChatOpenAI(
    azure_endpoint="https://ai-foundry-cv-pilot.openai.azure.com/",
    api_key=SecretStr(openai_api_key),
    azure_deployment="gpt-5.4-nano",  # your deployment name in Azure
    api_version="2024-10-21",
)

llm_with_structured_model = llm.with_structured_output(GroundedAnswer)


def build_context(rows: list[tuple]) -> tuple[str, list[str]]:
    # [(source, chunk_index, content, distance), ...]

    sources = []
    lines = []
    for source, chunk_index, content, dist in rows:
        lines.append(f"[{source}]  {content}")
        sources.append(source)

        print_color(
            f"    retrieved {source}#{chunk_index} "
            f"(distance={dist:.3f}, similarity={1 - dist:.3f})",
            Color.GRAY,
        )

    unique_source = list(dict.fromkeys(sources))
    context = "\n\n".join(lines)

    return (context, unique_source)


def search(conn, question: str, top_k: int = TOP_K) -> list[tuple]:
    q_vector = embed([question])[0]

    results = conn.execute(
        """
                 SELECT source, chunk_index, content,
                        embedding <=> %s::vector AS distance
                        FROM   chunks
                        ORDER BY embedding <=> %s::vector
                        LIMIT  %s   
                 """,
        (q_vector, q_vector, top_k),
    ).fetchall()

    return results


def main():
    test_fil_path = Path(__file__).parent / "inputs.json"
    test_suit = TestSuite.model_validate_json(test_fil_path.read_text())

    conn = get_connection()
    for index, case in enumerate(test_suit.cases[:8]):
        print_color(f"    question[{index}] : {case.question}", Color.PINK)
        vector_db_results = search(conn=conn, question=case.question)

        (context, retrieved_sources) = build_context(vector_db_results)

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
