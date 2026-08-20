import hashlib
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from shared_tools.utiles import Color, print_color

DOCS_DIR = str(Path(__file__).parent / "docs")
DB_DIR = str(Path(__file__).parent / "chroma_db")
COLLECTION_NAME = "handbook"

CHUNK_SIZE = 500  # characters (tune this later and watch what changes)
CHUNK_OVERLAP = 100


print(Path(DB_DIR).resolve())


embedder = SentenceTransformer("all-MiniLM-L6-v2")


def embed(texts: list[str]) -> list[list[float]]:
    """Turn a list of strings into a list of vectors (plain Python lists)."""
    return embedder.encode(texts).tolist()


def get_collection():
    """
    PersistentClient writes to a folder. Reopening the same folder later
    gives you the same data back - that is the whole point of this project.
    """
    client = chromadb.PersistentClient(path=DB_DIR)
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        configuration={"hnsw": {"space": "cosine"}},
        # older chromadb versions use: metadata={"hnsw:space": "cosine"}
    )


def reset_collection():
    """Delete the collection completely, then recreate it empty."""
    client = chromadb.PersistentClient(path=DB_DIR)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass  # it did not exist yet
    return get_collection()


def load_document_record(file_path: Path) -> dict | None:
    try:
        raw_bytes = file_path.read_bytes()
        file_hash = hashlib.sha256(raw_bytes).hexdigest()
        content = raw_bytes.decode("utf-8")
        print_color(f"[LOAD-FILE] succeed! name:'{file_path.name}'", Color.YELLOW)
        return {"source": file_path.name, "content": content, "file_hash": file_hash}
    except Exception as error:
        print_color(
            f"[LOAD-FILE] {file_path.name} | {type(error).__name__}: {error}",
            Color.RED,
        )
        return None


def load_documents(docs_dir: str) -> list[dict]:
    """
    Read every .md file in docs_dir.
    Return something like: [{"source": "onboarding.md", "text": "..."}, ...]
    """

    all_md_files = [f for f in Path(docs_dir).glob("*.md") if f.is_file()]

    results = []
    for file in all_md_files:
        document_record = load_document_record(file)
        if document_record:
            results.append(document_record)

    return results


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if overlap >= chunk_size:
        raise ValueError(
            f"overlap ({overlap}) must be smaller than chunk_size ({chunk_size})"
        )

    text_len = len(text)
    if text_len <= chunk_size:
        return [text]

    results = []
    start_index = 0

    while True:
        end_index = start_index + chunk_size
        if end_index >= text_len:
            results.append(text[start_index:])  # last chunk
            break

        end_index = find_boundary(text, start_index, end_index, chunk_size)

        results.append(text[start_index:end_index])
        start_index = end_index - overlap

    return results


SEPARATORS = ["\n\n", "\n", " "]


def find_boundary(text: str, start: int, end: int, chunk_size: int) -> int:
    """Return the best cut point at or before `end`, absolute index."""
    min_end = start + chunk_size // 2  # never cut too early

    for sep in SEPARATORS:
        index = text.rfind(sep, start, end)
        if index != -1 and index + len(sep) > min_end:
            return index + len(sep)

    return end  # no usable boundary -> hard cut


#################################################


def main():
    collection = reset_collection()

    documents_records = load_documents(DOCS_DIR)

    # Flat, parallel lists - one entry per CHUNK, not per file
    ids: list[str] = []
    texts: list[str] = []
    meta_datas: list[dict] = []

    for record in documents_records:
        chunks = chunk_text(
            record["content"], chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP
        )

        for chunk_index, chunk in enumerate(chunks):
            ids.append(f"{record['source']}#{chunk_index}")
            texts.append(chunk)

            meta_datas.append(
                {
                    "source": record["source"],
                    "chunk_index": chunk_index,
                    "file_hash": record["file_hash"],
                }
            )
        print_color(
            f"chunking file: '{record['source']}' into chunks:{len(chunks)}",
            Color.YELLOW,
        )
    if not texts:
        print_color("--> nothing to ingest, docs/ is empty", Color.RED)
        return

    max_tokens = embedder.max_seq_length
    for text in texts:
        n_tokens = len(embedder.tokenizer.encode(text))
        if n_tokens > max_tokens:
            raise ValueError(f"chunk too long: {n_tokens} tokens > {max_tokens}")

    print_color("embedding vectors", Color.GRAY)

    vectors = embed(texts)
    collection.add(ids=ids, embeddings=vectors, documents=texts, metadatas=meta_datas)

    print_color(
        f"--> files: {len(documents_records)} | chunks: {len(texts)} "
        f"| collection count: {collection.count()}",
        Color.GREEN,
    )


if __name__ == "__main__":
    main()
