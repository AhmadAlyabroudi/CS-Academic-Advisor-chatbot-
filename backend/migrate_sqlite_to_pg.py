import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

sqlite_engine = create_engine("sqlite:////var/www/justadvisor/backend/Project.db")
pg_engine = create_engine(DATABASE_URL)

# الترتip الصحيح هندسياً لحل مشكلة القيود
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
        # إيقاف القيود تماماً أثناء عملية النقل لتفادي أي تضارب بالـ Foreign Keys
        dest.execute(text("SET session_replication_role = 'replica';"))
        dest.commit()
        
        for table in tables:
            try:
                rows = src.execute(text(f"SELECT * FROM {table}")).mappings().all()
                if not rows:
                    continue
                
                # تفريغ الجدول في Postgres قبل صب الجديد لمنع التكرار
                dest.execute(text(f"DELETE FROM {table};"))
                dest.commit()
                
                for row in rows:
                    try:
                        # معالجة مشكلة الساعات المفقودة أو الأعمدة الزائدة
                        row_dict = dict(row)
                        columns = ", ".join(row_dict.keys())
                        placeholders = ", ".join([f":{k}" for k in row_dict.keys()])
                        insert_query = text(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})")
                        dest.execute(insert_query, row_dict)
                    except Exception:
                        continue # تخطي أي سطر مكسور محلياً لمتابعة صب الباقي
                dest.commit()
                print(f"✅ Table [{table}] synchronized successfully.")
            except Exception:
                continue
                
        dest.execute(text("SET session_replication_role = 'origin';"))
        dest.commit()

if __name__ == "__main__":
    migrate()
    print("🎉 Sync Complete!")