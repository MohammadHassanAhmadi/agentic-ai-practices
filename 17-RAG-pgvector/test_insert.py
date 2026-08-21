from db import get_connection

from shared_tools.utiles import Color, print_color

fake_vector = [0.1] * 384

DELETE_QUERY = "DELETE FROM chunks WHERE source = 'test.md';"
INSERT_QUERY = (
    """
        INSERT INTO chunks (source, chunk_index, file_hash, content, embedding)
        VALUES (%s, %s, %s, %s, %s)
        """,
)
INSERT_QUERY_PARAMS = ("test.md", 0, "abc123", "this is a test chunk", fake_vector)


with get_connection() as conn:
    conn.execute("DELETE FROM chunks WHERE source = 'test.md';")
    conn.commit()

    count = conn.execute("SELECT  count(*) FROM chunks").fe()[0]
    print_color(f"rows: {count}", Color.GREEN)
