from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from app.core.database import engine, Base, SessionLocal
from app.models.student import Student
from app.api.student_controller import router as student_router
from app.models.cs_faculty_info import CsFacultyInfo
from app.api.faculty_controller import router as faculty_router
from app.models.course import Course
from app.api.course_controller import router as course_router

# FastAPI app
app = FastAPI(
    title="CS Academic Advisor Chatbot API",
    description="Backend for the CS Academic Advisor Chatbot (Simplified).",
    version="0.1.0"
)

# Automigrate (create tables)
Base.metadata.create_all(bind=engine)


# Seed database
def seed():
    db = SessionLocal()
    try:
        # --- إضافة الطلاب ---
        students_data = [
            Student(
                university_id="160309",
                email="rymohaidat22@cit.just.edu.jo",
                first_name="Razan",
                last_name="Mohaidat",
                password="2004",
                phone_number="0776690165",
                academic_standing="fourth year"
            )
        ]
        for student in students_data:
            db.merge(student)

        # --- إضافة الدكاترة ---
        faculty_data = [
            CsFacultyInfo(
                email="yahyah@just.edu.jo",
                name="Dr. yahya tashtoush",
                office_location="A1L2",
                office_hours="Sun-Tue-Thu 09:00-12:00"
            )
        ]
        for member in faculty_data:
            db.merge(member)

        # --- 2. إضافة الكورسات (New Seeding) ---
        # ملاحظة: student_id يجب أن يطابق university_id الموجود أعلاه
        courses_data = [
            Course(
                code="CS101",
                name="Introduction to Programming",
                prerequisites="None",
                plan_type="Compulsory",
                credit_hours="3",
                year_and_semester="1st Year - 1st Sem",
            ),
            Course(
                code="SE103 ",
                name="Introduction to IT",
                prerequisites="None",
                plan_type="Compulsory",
                credit_hours="3",
                year_and_semester="1st Year - 1st Sem",
            )
        ]
        for course in courses_data:
            db.merge(course)

        db.commit()
        print("All data (Students, Faculty, Courses) synced successfully!")

    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
    finally:
        db.close()


# تنفيذ السدينج
seed()

# 3. تسجيل جميع الرواترز (Routes)
app.include_router(student_router)
app.include_router(faculty_router)
app.include_router(course_router)  # إضافة راوتر الكورسات هنا


# Mount static files
app.mount("/frontend", StaticFiles(directory="../frontend"), name="frontend")


@app.get("/", response_class=HTMLResponse)
def login_page():
    try:
        with open("../frontend/mainpage.html", "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        return "mainpage.html not found in frontend directory"