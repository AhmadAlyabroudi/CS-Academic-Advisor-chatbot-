import socketio
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from app.core.database import engine, Base, SessionLocal
from app.core.constants import GRADE_POINTS
from app.models.student import Student
from app.api.student_controller import router as student_router
from app.models.cs_faculty_info import CsFacultyInfo
from app.api.faculty_controller import router as faculty_router
from app.models.course import Course
from app.api.course_controller import router as course_router
from app.api.roadmap_controller import router as roadmap_router
from app.api.rooms_controller import router as rooms_router
from app.api.chatbot_controller import router as chatbot_router
from app.api.gpa_controller import router as gpa_router
from app.api.gpa_controller import router as gpa_router
from app.api.config_controller import router as config_router
from app.models.student_roadmap import StudentRoadmap
from app.models.study_rooms import OfficialRooms, PrivateStudyRooms
from app.models.chatbot_history import ChatbotHistory
from app.models.student_verification import StudentVerification
from app.core.socket_manager import sio
import app.api.signaling_controller  # noqa: F401 — registers socket events

# FastAPI app
app = FastAPI(
    title="CS Academic Advisor Chatbot API",
    description="Backend for the CS Academic Advisor Chatbot (Simplified).",
    version="0.1.0"
)

# تأمين بناء الجداول لضمان عدم انهيار التطبيق إذا كانت القاعدة ممتلئة أو غير جاهزة لحظياً
try:
    Base.metadata.create_all(bind=engine)
except Exception as db_err:
    print(f"Database tables warning (Alembic fallback): {db_err}")


def seed():
    """
    Seed ONLY universal reference data:
      - Faculty directory
      - CS curriculum (courses)
      - Official study rooms (one per course)
      - GPA recompute for every existing student (idempotent)
    """
    db = SessionLocal()
    try:
        # --- Faculty directory ---
        faculty_data = [
            CsFacultyInfo(name="Dr Ahmad G. Alzubi", email="agalzubi@just.edu.jo", office_location="A2L-O", office_hours="Sun 11:00 – 12:00", title="Associate Professor Chairman"),
            CsFacultyInfo(name="Dr Malak Abdel Ghani Abdullah", email="mabdullah@just.edu.jo", office_location="A1-L3", office_hours="Mon 12:00-1:00", title="Associate Professor"),
            CsFacultyInfo(name="Dr Mohammad Ahmad Alsmadi", email="maalsmadi9@just.edu.jo", office_location="C5 L-2", office_hours="Sun 10:00 – 12:00", title="Associate Professor"),
            CsFacultyInfo(name="Dr Mohammad Abdullah Alsmirat", email="masmirat@just.edu.jo", office_location="M2-L2", office_hours="Tue 1:00-2:00", title="Associate Professor"),
            CsFacultyInfo(name="Dr Mohammed Ibrahim Al-Saleh", email="misaleh@just.edu.jo", office_location="PH4 Level -1", office_hours="Wen 12:00-3:00", title="Associate Professor"),
            CsFacultyInfo(name="Dr Domar Abdel Karim Alzoubi", email="oaalzoubi@just.edu.jo", office_location="A1-L3", office_hours="Tue 1:00-2:00", title="Associate Professor"),
            CsFacultyInfo(name="Dr Omar Saad Almousa", email="osalmousa@just.edu.jo", office_location="A1-L3", office_hours="Thu 9:00-12:00", title="Associate Professor"),
            CsFacultyInfo(name="Dr Qanita Mohamad Bani Baker", email="qmbanibaker@just.edu.jo", office_location="A1-L3", office_hours="Sun 11:00 – 12:00", title="Associate Professor"),
            CsFacultyInfo(name="Dr Abdullah Mohammad Al-Amaren", email="amalamaren@just.edu.jo", office_location="A1-L3", office_hours="Wen 12:00-3:00", title="Assistant Professor"),
            CsFacultyInfo(name="Dr Ahmed Saleh Bataineh", email="asbataineh@just.edu.jo", office_location="A1-L3", office_hours="Wen 12:00-3:00", title="Assistant Professor"),
            CsFacultyInfo(name="Dr Ala' Issa Jararweh", email="aijararweh@just.edu.jo", office_location="A1-L3", office_hours="Sun 11:00 – 12:00", title="Assistant Professor"),
            CsFacultyInfo(name="Dr Alia Sayel Madain", email="asmadain@just.edu.jo", office_location="A1-L3", office_hours="Thu 9:00-12:00", title="Assistant Professor"),
            CsFacultyInfo(name="Dr Dana Monther Elrushaidat", email="dmelrushaidat@just.edu.jo", office_location="A1-L3", office_hours="Sun 11:00 – 12:00", title="Assistant Professor"),
            CsFacultyInfo(name="Dr Farah Mahmoud Alshanik", email="fmalshanik@just.edu.jo", office_location="A1-L3", office_hours="Sun 11:00 – 12:00", title="Assistant Professor"),
            CsFacultyInfo(name="Dr Mohammed Nayef Alrefai", email="mnalrefai@just.edu.jo", office_location="A1-L3", office_hours="Sun 11:00 – 12:00", title="Assistant Professor"),
            CsFacultyInfo(name="Dr Rasha Mohammad Obeidat", email="rmobeidat@just.edu.jo", office_location="A1-L3", office_hours="Sun 11:00 – 12:00", title="Assistant Professor"),
            CsFacultyInfo(name="Dr Tariq Mohammed Alomari", email="talomari@just.edu.jo", office_location="A1-L3", office_hours="Sun 11:00 – 12:00", title="Assistant Professor"),
            CsFacultyInfo(name="Dr Amer Fadeel Al-Badarneh", email="amerb@just.edu.jo", office_location="PH4 L0", office_hours="Sun 11:00 – 12:00", title="Professor"),
            CsFacultyInfo(name="Dr Firas Ali Al Balas", email="faalbalas@just.edu.jo", office_location="A1-L3", office_hours="Sun 11:00 – 12:00", title="Professor"),
            CsFacultyInfo(name="Dr Hassan Mohammad Najadat", email="najadat@just.edu.jo", office_location="A2 L3", office_hours="Sun 11:00 – 12:00", title="Professor"),
            CsFacultyInfo(name="Dr Ismail Ibrahim Hmeidi", email="hmeidi@just.edu.jo", office_location="PH4 L0", office_hours="Sun 11:00 – 12:00", title="Professor"),
            CsFacultyInfo(name="Dr Mahmoud Abdel-Karim Alshbool", email="maalshbool@just.edu.jo", office_location="PH4 L0", office_hours="Sun 11:00 – 12:00", title="Professor"),
            CsFacultyInfo(name="Dr Muneer Oqlah Bani Yasin", email="masadeh@just.edu.jo", office_location="A1L2", office_hours="Sun 11:00 – 12:00", title="Professor"),
            CsFacultyInfo(name="Dr Rehab Mustafa Duwairi", email="rehab@just.edu.jo", office_location="A2 3rd floor", office_hours="Sun 11:00 – 12:00", title="Professor"),
            CsFacultyInfo(name="Dr Sulieman Ahmad Bani-Ahmad", email="sabaniahmad@just.edu.jo", office_location="M2 - L 2", office_hours="Sun 11:00 – 12:00", title="Professor"),
            CsFacultyInfo(name="Dr Wail Elias Mardini", email="mardini@just.edu.jo", office_location="Engineering building A1 L3", office_hours="Sun 11:00 – 12:00", title="Professor"),
            CsFacultyInfo(name="Dr Yahya Mohammad Tashtoush", email="yahya-t@just.edu.jo", office_location="A1L3", office_hours="Sun 11:00 – 12:00", title="Professor"),
            CsFacultyInfo(name="Dr Yaser Ibrahim Jararweh", email="yijararweh@just.edu.jo", office_location="A1L3", office_hours="Sun 11:00 – 12:00", title="Professor"),
            CsFacultyInfo(name="Dr Abedl-rahman Abdul-Karim Almodawar", email="aaalmodawar@just.edu.jo", office_location="A1 L3", office_hours="Sun 11:00 – 12:00", title="Lecturer"),
            CsFacultyInfo(name="Dr Ghadeer Nazem Obeidat", email="gnobiedat@just.edu.jo", office_location="A1-L3", office_hours="Sun 11:00 – 12:00", title="Lecturer"),
            CsFacultyInfo(name="Dr Noor Adnan Zaghal", email="noorzaghal@just.edu.jo", office_location="A1 L3", office_hours="Sun 11:00 – 12:00", title="Lecturer"),
            CsFacultyInfo(name="Dr Wafa' Ahmad Alqarqaz", email="waalqarqaz@just.edu.jo", office_location="A1 L3", office_hours="Sun 11:00 – 12:00", title="Lecturer"),
        ]
        for member in faculty_data:
            db.merge(member)

        # --- CS curriculum (universal course catalog) ---
        courses_data = [
            # Year 1 - Fall
            Course(code="LG101", id_reg="2511010", name="Communication Skills In English", prerequisites="LG 099", plan_type="University Compulsory Req", credit_hours=3, suggested_year=1, suggested_semester="Fall"),
            Course(code="CS101", id_reg="821018", name="Introduction to Programming", prerequisites="None", plan_type="Faculty Compulsory Req", credit_hours=2, suggested_year=1, suggested_semester="Fall"),
            Course(code="CS106", id_reg="821061", name="Introduction to Programming lab", prerequisites="CS101", plan_type="Faculty Compulsory Req", credit_hours=1, suggested_year=1, suggested_semester="Fall"),
            Course(code="SE103", id_reg="821037", name="Introduction to Information Technology", prerequisites="None", plan_type="Faculty Compulsory Req", credit_hours=3, suggested_year=1, suggested_semester="Fall"),
            Course(code="MATH101", id_reg="821011", name="Calculus I", prerequisites="None", plan_type="Faculty Compulsory Req", credit_hours=3, suggested_year=1, suggested_semester="Fall"),
            Course(code="MS100", id_reg="841000", name="Military Sciences", prerequisites="None", plan_type="University Compulsory Req", credit_hours=3, suggested_year=1, suggested_semester="Fall"),
            Course(code="PHY102", id_reg="821024", name="General Physics (2)", prerequisites="None", plan_type="Faculty Compulsory Req", credit_hours=3, suggested_year=1, suggested_semester="Fall"),

            # Year 1 - Spring
            Course(code="SE112", id_reg="821123", name="Introduction To Object-Oriented Programming", prerequisites="CS101", plan_type="Faculty Compulsory Req", credit_hours=2, suggested_year=1, suggested_semester="Spring"),
            Course(code="SE113", id_reg="821124", name="Introduction To Object-Oriented Programming lab", prerequisites="SE112", plan_type="Faculty Compulsory Req", credit_hours=1, suggested_year=1, suggested_semester="Spring"),
            Course(code="MATH102", id_reg="821023", name="Calculus 2", prerequisites="MATH 101", plan_type="Faculty Compulsory Req", credit_hours=3, suggested_year=1, suggested_semester="Spring"),
            Course(code="MATH241", id_reg="822411", name="Discrete Mathematics", prerequisites="MATH 101", plan_type="Faculty Compulsory Req", credit_hours=3, suggested_year=1, suggested_semester="Spring"),
            Course(code="HSS110", id_reg="821104", name="Leader And Social Responsibility", prerequisites="None", plan_type="University Compulsory Req", credit_hours=3, suggested_year=1, suggested_semester="Spring"),
            Course(code="ARB102", id_reg="801022", name="Communication Skills In Arabic", prerequisites="None", plan_type="University Compulsory Req", credit_hours=3, suggested_year=1, suggested_semester="Spring"),
            Course(code="PHY106", id_reg="921060", name="General Physics (Laboratory)(2)", prerequisites="PHY 102", plan_type="Faculty Compulsory Req", credit_hours=1, suggested_year=1, suggested_semester="Spring"),

            # Year 2 - Fall
            Course(code="HSS119", id_reg="821192", name="Entrepreneurship And Innovation", prerequisites="None", plan_type="University Compulsory Req", credit_hours=2, suggested_year=2, suggested_semester="Fall"),
            Course(code="CIS201", id_reg="1742010", name="Introduction to Web Design", prerequisites="CS101", plan_type="Department Compulsory Req.", credit_hours=1, suggested_year=2, suggested_semester="Fall"),
            Course(code="CS216", id_reg="1732160", name="Object-Oriented Software Modeling Lab", prerequisites="CS101", plan_type="Department Compulsory Req.", credit_hours=1, suggested_year=2, suggested_semester="Fall"),
            Course(code="LG103", id_reg="2511030", name="Life Skills", prerequisites="None", plan_type="University Compulsory Req", credit_hours=2, suggested_year=2, suggested_semester="Fall"),
            Course(code="CS211", id_reg="822112", name="Data Structures", prerequisites="MATH241&CS101", plan_type="Faculty Compulsory Req", credit_hours=3, suggested_year=2, suggested_semester="Fall"),
            Course(code="MATH140", id_reg="901400", name="Elements Of Linear Algebra", prerequisites="MATH101", plan_type="Department Compulsory Req.", credit_hours=3, suggested_year=2, suggested_semester="Fall"),
            Course(code="CIS203", id_reg="1742031", name="Communication and Professional Ethics", prerequisites="None", plan_type="Faculty Compulsory Req", credit_hours=2, suggested_year=2, suggested_semester="Fall"),
            Course(code="UnivElec1", id_reg="None", name="University Elective Requisite", prerequisites="None", plan_type="University Elective Requisite", credit_hours=3, suggested_year=2, suggested_semester="Fall"),

            # Year 2 - Spring
            Course(code="CPE231", id_reg="1712310", name="Digital Logic Design", prerequisites="None", plan_type="Department Compulsory Req.", credit_hours=3, suggested_year=2, suggested_semester="Spring"),
            Course(code="CS282", id_reg="1732821", name="Theory of Computing", prerequisites="MATH241&CS101", plan_type="Department Compulsory Req.", credit_hours=3, suggested_year=2, suggested_semester="Spring"),
            Course(code="CS284", id_reg="1732841", name="Analysis and Design of Algorithms", prerequisites="CS211", plan_type="Department Compulsory Req.", credit_hours=3, suggested_year=2, suggested_semester="Spring"),
            Course(code="CIS221", id_reg="822214", name="Fundamentals of Database Systems", prerequisites="CS211", plan_type="Faculty Compulsory Req", credit_hours=3, suggested_year=2, suggested_semester="Spring"),
            Course(code="MATH233", id_reg="822331", name="MATH Probability & Statistics", prerequisites="MATH102", plan_type="Department Compulsory Req.", credit_hours=3, suggested_year=2, suggested_semester="Spring"),

            # Year 3 - Fall
            Course(code="CPE232", id_reg="1712320", name="Digital Logic Design Lab", prerequisites="CPE 231", plan_type="Department Compulsory Req.", credit_hours=1, suggested_year=3, suggested_semester="Fall"),
            Course(code="CS318", id_reg="1733180", name="Human-Computer Interaction", prerequisites="CS211", plan_type="Department Compulsory Req.", credit_hours=3, suggested_year=3, suggested_semester="Fall"),
            Course(code="CS342", id_reg="1733420", name="Computer Networks", prerequisites="CS284", plan_type="Department Compulsory Req.", credit_hours=3, suggested_year=3, suggested_semester="Fall"),
            Course(code="CPE252", id_reg="1712520", name="Computer Organization and Design", prerequisites="CPE231", plan_type="Department Compulsory Req.", credit_hours=3, suggested_year=3, suggested_semester="Fall"),
            Course(code="SE230", id_reg="1762300", name="Fundamentals of Software Engineering", prerequisites="CS216", plan_type="Department Compulsory Req.", credit_hours=3, suggested_year=3, suggested_semester="Fall"),
            Course(code="UnivElec2", id_reg="None", name="University Elective Requisite", prerequisites="None", plan_type="University Elective Requisite", credit_hours=3, suggested_year=3, suggested_semester="Fall"),

            # Year 3 - Spring
            Course(code="CS362", id_reg="1733620", name="Artificial Intelligence", prerequisites="CS284", plan_type="Department Compulsory Req.", credit_hours=3, suggested_year=3, suggested_semester="Spring"),
            Course(code="CS375", id_reg="1733750", name="Operating Systems", prerequisites="CS284&CPE252", plan_type="Department Compulsory Req.", credit_hours=3, suggested_year=3, suggested_semester="Spring"),
            Course(code="CS385", id_reg="1733850", name="Fundamentals of Multimedia", prerequisites="MATH140&CS211", plan_type="Department Compulsory Req.", credit_hours=3, suggested_year=3, suggested_semester="Spring"),
            Course(code="SE320", id_reg="1763200", name="System Analysis and Design", prerequisites="CIS221&SE230", plan_type="Department Compulsory Req.", credit_hours=3, suggested_year=3, suggested_semester="Spring"),
            Course(code="UnivElec3", id_reg="None", name="University Elective Requisite", prerequisites="None", plan_type="University Elective Requisite", credit_hours=3, suggested_year=3, suggested_semester="Spring"),

            # Year 3 - Summer
            Course(code="CS391", id_reg="1733910", name="Practical Training", prerequisites="PASS 90 Credit", plan_type="Department Compulsory Req.", credit_hours=3, suggested_year=3, suggested_semester="Summer"),

            # Year 4 - Fall
            Course(code="CS451", id_reg="1734511", name="Computer Architecture", prerequisites="CPE252&CS375", plan_type="Department Compulsory Req.", credit_hours=3, suggested_year=4, suggested_semester="Fall"),
            Course(code="CS491", id_reg="1734911", name="Graduation Project 1", prerequisites="PASS 90 Credit", plan_type="Department Compulsory Req.", credit_hours=3, suggested_year=4, suggested_semester="Fall"),
            Course(code="CY261", id_reg="1772610", name="Cryptography", prerequisites="SE112&SE113&MATH233", plan_type="Department Compulsory Req.", credit_hours=3, suggested_year=4, suggested_semester="Fall"),
            Course(code="BT401", id_reg="964010", name="Computational Biology", prerequisites="CS101", plan_type="Department Compulsory Req.", credit_hours=2, suggested_year=4, suggested_semester="Fall"),
            Course(code="BT401L", id_reg="964011", name="Computational Biology lab", prerequisites="BT401", plan_type="Department Compulsory Req.", credit_hours=0, suggested_year=4, suggested_semester="Fall"),
            Course(code="DeptElec1", id_reg="None", name="Department Elective Requisite", prerequisites="None", plan_type="Department Elective", credit_hours=3, suggested_year=4, suggested_semester="Fall"),
            Course(code="DeptElec2", id_reg="None", name="Department Elective Requisite", prerequisites="None", plan_type="Department Elective", credit_hours=3, suggested_year=4, suggested_semester="Fall"),

            # Year 4 - Spring
            Course(code="CS442", id_reg="1734421", name="Wireless Networks", prerequisites="CS342", plan_type="Department Compulsory Req.", credit_hours=3, suggested_year=4, suggested_semester="Spring"),
            Course(code="CS475", id_reg="1734751", name="Distributed Computer Systems", prerequisites="CS375&CS451", plan_type="Department Compulsory Req.", credit_hours=3, suggested_year=4, suggested_semester="Spring"),
            Course(code="CS492", id_reg="1734921", name="Graduation Project 2", prerequisites="CS491", plan_type="Department Compulsory Req.", credit_hours=3, suggested_year=4, suggested_semester="Spring"),
            Course(code="CIS341", id_reg="1743410", name="Web Applications Development", prerequisites="CIS201&SC318", plan_type="Department Compulsory Req.", credit_hours=3, suggested_year=4, suggested_semester="Spring"),
            Course(code="DeptElec3", id_reg="1734751", name="Department Elective Requisite", prerequisites="None", plan_type="Department Elective", credit_hours=3, suggested_year=4, suggested_semester="Spring"),
        ]
        for course in courses_data:
            db.merge(course)

        db.commit()

        # --- Official rooms ---
        all_courses = db.query(Course).all()
        for course in all_courses:
            existing = db.query(OfficialRooms).filter_by(course_code=course.code).first()
            if not existing:
                db.add(OfficialRooms(course_code=course.code))

        db.commit()

        # --- Student verification whitelist ---
        verification_data = [
            StudentVerification(email="ymtashtoush@cit.just.edu.jo",    university_id="160991"),
            StudentVerification(email="rymohaidat22@cit.just.edu.jo.jo", university_id="160309"),
            StudentVerification(email="csalnimri22@cit.just.edu.jo",   university_id="162256"),
        ]
        for v in verification_data:
            existing_v = db.query(StudentVerification).filter_by(email=v.email).first()
            if not existing_v:
                db.add(v)

        db.commit()

        # --- Recalculate GPA ---
        all_students = db.query(Student).all()
        for stu in all_students:
            items = db.query(StudentRoadmap).filter_by(student_id=stu.university_id).all()
            total_points = 0.0
            total_credits = 0.0
            for item in items:
                if (item.status or "").lower() != "completed":
                    continue
                grade = (item.grade or "").upper()
                if grade not in GRADE_POINTS:
                    continue
                course = db.query(Course).filter(Course.code == item.course_code).first()
                if not course or not course.credit_hours:
                    continue
                credits = float(course.credit_hours)
                total_points += GRADE_POINTS[grade] * credits
                total_credits += credits
            if total_credits > 0:
                stu.current_gpa = round(total_points / total_credits, 2)
        db.commit()

        print("Seed complete — universal data (faculty, courses, official rooms) synced.")

    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
    finally:
        db.close()


# حماية تشغيل الـ seed ليعمل فقط في البيئة الحية وليس عند استيراد الملف بشكل مكرر
if __name__ == "__main__":
    seed()

# Register REST routers
app.include_router(student_router)
app.include_router(faculty_router)
app.include_router(course_router)
app.include_router(roadmap_router)
app.include_router(rooms_router)
app.include_router(chatbot_router)
app.include_router(gpa_router)
app.include_router(config_router)

# Mount static files
app.mount("/frontend", StaticFiles(directory="../frontend"), name="frontend")


@app.get("/")
def root():
    return RedirectResponse(url="/frontend/index.html")


# Wrap FastAPI with Socket.IO — this is the ASGI app that uvicorn/gunicorn runs
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)