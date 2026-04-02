# Initialize PostgreSQL: doc_hashes (legacy) and optional analysis tables created at runtime by the app.
import os

import psycopg2


def get_conn():
    return psycopg2.connect(
        host=os.getenv("PG_HOST", "localhost"),
        port=os.getenv("PG_PORT", "5432"),
        dbname=os.getenv("PG_DB", "chakravyuh"),
        user=os.getenv("PG_USER", "chakravyuh"),
        password=os.getenv("PG_PASSWORD", "chakravyuh"),
    )


def init_db():
    commands = [
        """
        CREATE TABLE IF NOT EXISTS doc_hashes (
            id SERIAL PRIMARY KEY,
            doc_name TEXT NOT NULL,
            service TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW(),
            UNIQUE (doc_name, service)
        );
        """
    ]

    with get_conn() as conn, conn.cursor() as cur:
        for cmd in commands:
            try:
                cur.execute(cmd)
            except Exception as e:
                print(f"⚠️ Skipped command due to error: {e}")
        conn.commit()

    print("✅ Database initialized (doc_hashes). analysis_sessions is created by the API on first use.")


if __name__ == "__main__":
    init_db()
