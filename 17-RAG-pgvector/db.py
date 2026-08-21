import os

import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector

from shared_tools.utiles import Color, print_color

load_dotenv(override=True)

DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection() -> psycopg.Connection:
    """Open a connection that understands the vector type."""
    conn = psycopg.connect(DATABASE_URL)
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    register_vector(conn)
    return conn


if __name__ == "__main__":
    with get_connection() as conn:
        row = conn.execute("SELECT count(*) FROM chunks").fetchone()
        print_color(f"rows in chunk: {row[0]}", Color.GREEN)
