from hashlib import sha256
from pathlib import Path

import psycopg
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

from shared_tools.utiles import Color, print_color

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", " ", ""],
    length_function=len,
)

print_color("initializing model... [ all-MiniLM-L6-v2 ]", Color.BLUE)
sentence_transformer = SentenceTransformer("all-MiniLM-L6-v2")
print_color("model loaded", Color.BLUE)


def load_documents(docs_dir: str, pattern: str = "*.md") -> list[dict]:
    if pattern not in ["*.md", "*.txt"]:
        raise NotImplementedError(f"not yet supported files of type {pattern}")

    files = [f for f in sorted(Path(docs_dir).glob(pattern)) if f.is_file()]

    print_color(f"founded files for loading, count:{len(files)}", Color.GRAY)

    documents = []
    for file in files:
        raw_byte = file.read_bytes()

        documents.append(
            {
                "source": file.name,
                "content": raw_byte.decode("utf-8"),
                "file_hash": sha256(raw_byte).hexdigest(),
            }
        )
    return documents


def embed(texts: list[str]) -> list[list[float]]:
    """Turn a list of strings into a list of vectors (plain Python lists)."""
    max_tokens = sentence_transformer.max_seq_length
    for text in texts:
        n_tokens = len(sentence_transformer.tokenizer.tokenize(text))
        if max_tokens is not None and n_tokens > max_tokens:
            raise ValueError(f"chunk too long: {n_tokens} tokens > {max_tokens}")

    return sentence_transformer.encode(texts).tolist()


def save_chunks(conn: psycopg.Connection, records: list[dict]) -> None:
    list_of_tuples = []
    for r in records:
        list_of_tuples.append(
            (
                r["source"],
                r["chunk_index"],
                r["file_hash"],
                r["content"],
                r["embedding"],
            )
        )

    with conn.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO chunks (source, chunk_index, file_hash, content, embedding)
            VALUES (%s, %s, %s, %s, %s)
            """,
            list_of_tuples,
        )
        print_color(f"Inserted count: {cursor.rowcount}", Color.GRAY)


DOCS_DIR = str(Path(__file__).parent / "docs")
from db import get_connection


def reset_table(connection):
    print_color("Truncating chunks", Color.GRAY)
    connection.execute("TRUNCATE chunks RESTART IDENTITY;")
    print_color("Truncating chunks completed", Color.GRAY)


if __name__ == "__main__":
    connection = get_connection()

    reset_table(connection)

    documents = load_documents(DOCS_DIR)
    chunked_texts_list = []
    records = []
    for doc in documents:
        source = doc["source"]
        file_hash = doc["file_hash"]
        chunks = splitter.split_text(doc["content"])

        for chunk_index, chunk in enumerate(chunks):
            chunked_texts_list.append(chunk)
            records.append(
                {
                    "source": source,
                    "chunk_index": chunk_index,
                    "file_hash": file_hash,
                    "content": chunk,
                }
            )
    print("chunked_texts_list:", len(chunked_texts_list))
    print("records:", len(records))

    vectors = embed(chunked_texts_list)

    for chunk_vector, record in zip(vectors, records):
        record["embedding"] = chunk_vector

    save_chunks(connection, records)
    connection.commit()

    result = connection.execute("SELECT count(*) FROM chunks").fetchone()[0]
    print(f"count: {result}")
