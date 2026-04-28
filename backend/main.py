from fastapi import FastAPI
from app.core.database import engine, Base, SessionLocal
from app.models.student import Student
from app.api.student_controller import router as student_router
from app.models.cs_faculty_info import CsFacultyInfo
from app.api.faculty_controller import router as faculty_router

# FastAPI app
app = FastAPI(
    title="CS Academic Advisor Chatbot API",
    description="Backend for the CS Academic Advisor Chatbot (Simplified).",
    version="0.1.0"
)

# Automigrate (create tables)
# ملاحظة: هذا السطر ينشئ الجداول إذا لم تكن موجودة
Base.metadata.create_all(bind=engine)


# Seed database
def seed():
    db = SessionLocal()
    try:
        # قسم الطلاب
        students_data = [
            Student(
                university_id="166001",  # المفتاح الأساسي
                email="amalyabroudi22@cit.just.edu.jo",
                first_name="Ahmad",
                last_name="Alyabroudi",
                password="2004",
                phone_number="0795753919",
                academic_standing="fourth year"
            )
        ]
        for student in students_data:
            db.merge(student)  # يمنع التكرار بناءً على university_id

        # قسم الدكاترة
        faculty_data = [
            CsFacultyInfo(
                email="yahyah@just.edu.jo",  # المفتاح الأساسي
                name="Dr. yahya tashtoush",
                office_location="A1L2",
                office_hours="Sun-Tue-Thu 09:00-12:00"
            )
        ]
        for member in faculty_data:
            db.merge(member)  # يمنع التكرار بناءً على email

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()


# استدعاء الدالة عند تشغيل السيرفر
seed()

# Register routes
app.include_router(student_router)
app.include_router(faculty_router)


@app.get("/", tags=["Root"])
def read_root():
    """
    Returns a simple hello world message.
    """
    return {"Hello": "Root"}