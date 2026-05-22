import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

sqlite_engine = create_engine("sqlite:////var/www/justadvisor/backend/Project.db")
pg_engine = create_engine(DATABASE_URL)

# الترتيب الصحيح
tables = [
    "student_verification",
    "cs_faculty_info",
    "courses",
    "students",
    "official_rooms",
    "private_study_rooms",
    "room_members",
    "student_roadmap",
    "chatbot_history",
    "enrollment"
]


def migrate():
    print("🚀 Starting Production Data Migration...")
    with sqlite_engine.connect() as src, pg_engine.connect() as dest:

        for table in tables:
            try:
                rows = src.execute(text(f"SELECT * FROM {table}")).mappings().all()
                if not rows:
                    print(f"⚠️ Table [{table}] is empty in SQLite. Skipping...")
                    continue

                print(f"📦 Found {len(rows)} rows for table [{table}]. Migrating...")

                # تنظيف الجدول قبل الصب لمنع التكرار
                dest.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER ALL;"))  # إيقاف القيود مؤقتاً لهذا الجدول
                dest.execute(text(f"DELETE FROM {table};"))
                dest.commit()

                for row in rows:
                    try:
                        row_dict = dict(row)
                        columns = ", ".join(row_dict.keys())
                        placeholders = ", ".join([f":{k}" for k in row_dict.keys()])
                        insert_query = text(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})")
                        dest.execute(insert_query, row_dict)
                    except Exception as row_err:
                        print(f"   ❌ Row insert error: {str(row_err)}")
                        continue

                dest.execute(text(f"ALTER TABLE {table} ENABLE TRIGGER ALL;"))  # إعادة تفعيل القيود
                dest.commit()
                print(f"✅ Table [{table}] synchronized successfully.")
            except Exception as e:
                print(f"❌ Critical error on table [{table}]: {str(e)}")
                continue


if __name__ == "__main__":
    migrate()
    print("🎉 Sync Complete!")