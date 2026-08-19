import time

from app import openai_api_key
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel, Field, SecretStr
from sentence_transformers import SentenceTransformer

load_dotenv()

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")  # ~ 90 MB

# llm = ChatGoogleGenerativeAI(
#     model="gemini-3.6-flash",
#     google_api_key=os.getenv("GOOGLE_AI_API_KEY"),
#     temperature=0,
# )


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


def answer(question: str, context: str) -> GroundedAnswer:
    prompt = f"""Answer the question using ONLY the context below.
    If the answer is not in the context, say "I don't know".
    Do not use any outside knowledge.
    Each context line starts with its source in square brackets.
    In used_sources return ONLY the sources you actually used. If none, return an empty list.

    Context:
    {context}

    Question: {question}"""

    return llm_with_structured_model.invoke(prompt)


docs = [
    {
        "text": "To terminate your plan, open Billing and click Close Account.",
        "source": "billing.md",
    },
    {
        "text": "Our support team is available Monday to Friday, 9am to 5pm.",
        "source": "contact.md",
    },
    {
        "text": "Refunds are processed within 14 business days of the request.",
        "source": "refund-policy.md",
    },
    {
        "text": "You can change your password from the Security tab in Settings.",
        "source": "account-security.md",
    },
    {
        "text": "Enterprise customers get a dedicated account manager.",
        "source": "enterprise-plan.md",
    },
    {
        "text": "Invoices are sent by email on the first day of each month.",
        "source": "billing.md",
    },
]

doc_vectors = embedding_model.encode([d["text"] for d in docs])
MIN_SCORE = 0.1  # only filter obvious garbage;


def search(question: str, top_k: int = 2):
    scores = embedding_model.similarity(embedding_model.encode(question), doc_vectors)[
        0
    ]
    results = [(float(s), d) for s, d in zip(scores, docs)]
    results = [r for r in results if r[0] >= MIN_SCORE]
    results.sort(key=lambda pair: pair[0], reverse=True)

    return results[:top_k]


questions = [
    "how do I cancel my subscription?",  # expect doc 1,
    "when will I get my money back?",  # expect doc 3,
    "who do I talk to for help?",
    "what is the weather in Toronto?",  # expect doc 2 or 5,
]

for question in questions:
    print("=" * 20)
    print(f"[Question] : {question}")

    relevant_chunks = search(question, 3)

    if len(relevant_chunks) == 0:
        print("[--No Answer found--]")
        continue

    context = "\n".join([f"[{c['source']}] {c['text']}" for (_, c) in relevant_chunks])
    grounded_answer = answer(question=question, context=context)

    print(f"[Answer]   : {grounded_answer.answer}")
    print(f"[Sources] : {grounded_answer.used_sources}")
    print()

    time.sleep(1)
