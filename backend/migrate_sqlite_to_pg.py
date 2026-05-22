import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL is not set in .env")
    sys.exit(1)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

SQLITE_PATH = os.getenv("SQLITE_PATH", str(Path(__file__).parent / "Project.db"))

# FK-ordered: parent tables first, child tables last
TABLES_FK_ORDER = [
    "student_verification",
    "cs_faculty_info",
    "courses",
    "students",
    "official_rooms",
    "private_study_rooms",
    "room_members",
    "student_roadmap",
    "chatbot_history",
    "enrollment",
]


def migrate() -> None:
    if not Path(SQLITE_PATH).exists():
        print(f"ERROR: SQLite database not found at {SQLITE_PATH}")
        sys.exit(1)

    print("=" * 60)
    print("  JUST Advisor — SQLite → PostgreSQL Data Migration")
    print("=" * 60)
    print(f"  Source : {SQLITE_PATH}")
    print(f"  Target : PostgreSQL ({DATABASE_URL.split('@')[-1]})")
    print()

    sqlite_engine = create_engine(f"sqlite:///{SQLITE_PATH}")
    pg_engine = create_engine(DATABASE_URL)

    # ── Step 1: read all data from SQLite ─────────────────────────────────────
    data: dict[str, list[dict]] = {}
    with sqlite_engine.connect() as src:
        for table in TABLES_FK_ORDER:
            try:
                rows = src.execute(text(f"SELECT * FROM {table}")).mappings().all()
                data[table] = [dict(r) for r in rows]
                print(f"  Read  [{table}]: {len(data[table])} rows")
            except Exception as e:
                print(f"  WARN  [{table}]: could not read from SQLite — {e}")
                data[table] = []

    # ── Step 2: clear PostgreSQL tables (CASCADE handles FK order) ─────────────
    print("\n[1/2] Clearing PostgreSQL tables...")
    all_tables = ", ".join(TABLES_FK_ORDER)
    with pg_engine.connect() as dest:
        dest.execute(text(
            f"TRUNCATE TABLE {all_tables} RESTART IDENTITY CASCADE"
        ))
        dest.commit()
    print("  All tables cleared.")

    # ── Step 3: insert in FK order (parents before children) ──────────────────
    print("\n[2/2] Inserting rows into PostgreSQL...")
    total_inserted = 0
    with pg_engine.connect() as dest:
        for table in TABLES_FK_ORDER:
            rows = data[table]
            if not rows:
                print(f"  SKIP  [{table}]: no data in SQLite")
                continue

            inserted = 0
            skipped = 0
            for row in rows:
                columns = ", ".join(row.keys())
                placeholders = ", ".join([f":{k}" for k in row.keys()])
                sql = text(
                    f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
                    f" ON CONFLICT DO NOTHING"
                )
                try:
                    dest.execute(sql, row)
                    inserted += 1
                except Exception as e:
                    skipped += 1
                    print(f"    ROW ERROR [{table}]: {e}")

            dest.commit()
            total_inserted += inserted
            status = "✓" if skipped == 0 else "!"
            print(f"  {status}  [{table}]: {inserted} inserted, {skipped} skipped")

    print(f"\n{'=' * 60}")
    print(f"  Migration complete — {total_inserted} total rows inserted.")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    migrate()
