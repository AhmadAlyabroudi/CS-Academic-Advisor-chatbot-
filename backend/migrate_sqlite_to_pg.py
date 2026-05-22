"""
One-time migration: copy all data from the local SQLite database to PostgreSQL.

Usage (run from the backend/ directory):
    DATABASE_URL=postgresql://user:pass@host/db python migrate_sqlite_to_pg.py

The script reads every row from the SQLite file and inserts it into the
PostgreSQL database, respecting foreign-key order.  It is idempotent — rows
that already exist (matched by primary key) are skipped.
"""

import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()

PG_URL = os.getenv("DATABASE_URL", "")
SQLITE_URL = "sqlite:///./Project.db"

if not PG_URL or not PG_URL.startswith("postgresql"):
    sys.exit("ERROR: Set DATABASE_URL to a postgresql:// URL before running this script.")

sqlite_engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
pg_engine = create_engine(PG_URL, pool_pre_ping=True)

SqliteSession = sessionmaker(bind=sqlite_engine)
PgSession = sessionmaker(bind=pg_engine)

# Tables in insertion order (respects FK dependencies)
TABLES = [
    "cs_faculty_info",
    "courses",
    "students",
    "student_roadmap",
    "student_verification",
    "official_rooms",
    "private_study_rooms",
    "room_members",
    "chatbot_history",
]


def migrate():
    src = SqliteSession()
    dst = PgSession()
    try:
        for table in TABLES:
            rows = src.execute(text(f"SELECT * FROM {table}")).mappings().all()
            if not rows:
                print(f"  {table}: 0 rows — skipped")
                continue

            cols = list(rows[0].keys())
            placeholders = ", ".join(f":{c}" for c in cols)
            col_list = ", ".join(cols)
            inserted = 0
            skipped = 0

            for row in rows:
                row_dict = dict(row)
                try:
                    dst.execute(
                        text(f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"),
                        row_dict,
                    )
                    dst.commit()
                    inserted += 1
                except Exception:
                    dst.rollback()
                    skipped += 1

            print(f"  {table}: {inserted} inserted, {skipped} skipped (duplicates/errors)")

        print("\nMigration complete.")
    finally:
        src.close()
        dst.close()


if __name__ == "__main__":
    print(f"Migrating from SQLite → {PG_URL[:40]}...\n")
    migrate()
