import re
from fastapi import APIRouter, Depends, HTTPException, status, Form
from passlib.context import CryptContext
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.constants import GRADE_POINTS
from app.models.student import Student
from app.models.student_roadmap import StudentRoadmap
from app.models.course import Course
from app.models.student_verification import StudentVerification
from app.schemas.student import StudentLogin, StudentUpdate, StudentPasswordUpdate, StudentSignup

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def validate_password_strength(password: str):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit."
    if not re.search(r"[@$!%*?&]", password):
        return False, "Password must contain at least one special character (@$!%*?&)."
    return True, ""


@router.get("/students", tags=["Students"])
def get_students(db: Session = Depends(get_db)):
    students = db.query(Student).all()
    return [
        {
            "university_id": s.university_id,
            "first_name": s.first_name,
            "last_name": s.last_name,
            "email": s.email,
            "major": s.major,
            "academic_standing": s.academic_standing,
            "current_gpa": s.current_gpa,
        }
        for s in students
    ]


@router.get("/student/{student_id}", tags=["Students"])
def get_student(student_id: str, db: Session = Depends(get_db)):
    student = db.query(Student).options(joinedload(Student.advisor)).filter(Student.university_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    completed_courses = db.query(StudentRoadmap).filter(
        StudentRoadmap.student_id == student_id,
        StudentRoadmap.status == "Completed"
    ).all()

    completed_codes = [rc.course_code for rc in completed_courses]
    courses_info = db.query(Course).filter(Course.code.in_(completed_codes)).all()
    completed_credits = sum(c.credit_hours for c in courses_info)

    total_curriculum_credits = 132
    remaining_credits = total_curriculum_credits - completed_credits

    advisor_info = None
    if student.advisor:
        advisor_info = {
            "name": student.advisor.name,
            "email": student.advisor.email,
            "title": student.advisor.title
        }

    return {
        "university_id": student.university_id,
        "first_name": student.first_name,
        "last_name": student.last_name,
        "email": student.email,
        "phone_number": student.phone_number,
        "major": student.major,
        "current_gpa": student.current_gpa,
        "academic_standing": student.academic_standing,
        "advisor": advisor_info,
        "completed_credits": completed_credits,
        "remaining_credits": remaining_credits
    }


@router.post("/login", tags=["Authentication"])
def login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    email = email.strip()
    password = password.strip()

    student = db.query(Student).filter(Student.email.ilike(email)).first()

    if not student:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User with this email not found.",
        )

    # Support bcrypt-hashed passwords; fall back to plaintext for legacy accounts
    # and immediately re-hash them on successful login.
    if pwd_context.identify(student.password):
        authenticated = pwd_context.verify(password, student.password)
    else:
        authenticated = (student.password == password)
        if authenticated:
            student.password = pwd_context.hash(password)
            db.commit()

    if not authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password.",
        )

    return {"message": "Login successful", "student_id": student.university_id}


@router.put("/student/{student_id}", tags=["Students"])
def update_student(student_id: str, student_update: StudentUpdate, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.university_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    student.first_name = student_update.first_name
    student.last_name = student_update.last_name
    student.phone_number = student_update.phone_number
    db.commit()
    db.refresh(student)
    return {
        "message": "Student updated successfully",
        "first_name": student.first_name,
        "last_name": student.last_name,
        "phone_number": student.phone_number
    }


@router.put('/student/{student_id}/password', tags=['Students'])
def update_student_password(student_id: str, password_update: StudentPasswordUpdate, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.university_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail='Student not found')

    # Verify current password (supports both hashed and legacy plaintext)
    if pwd_context.identify(student.password):
        current_ok = pwd_context.verify(password_update.current_password, student.password)
    else:
        current_ok = (student.password == password_update.current_password)

    if not current_ok:
        raise HTTPException(status_code=400, detail='Incorrect current password')

    is_strong, msg = validate_password_strength(password_update.new_password)
    if not is_strong:
        raise HTTPException(status_code=400, detail=msg)

    student.password = pwd_context.hash(password_update.new_password)
    db.commit()
    return {'message': 'Password updated successfully'}


@router.post("/signup", tags=["Authentication"])
def signup(signup_data: StudentSignup, db: Session = Depends(get_db)):
    # 1. Verify email + university_id are present in the verification whitelist.
    #    Only pre-approved students (seeded in main.py / inserted by admin into
    #    student_verification) are allowed to register.
    verification = db.query(StudentVerification).filter(
        StudentVerification.email.ilike(signup_data.email),
        StudentVerification.university_id == signup_data.university_id
    ).first()
    if not verification:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your email and university ID are not registered in the system."
        )

    # 2. Check for duplicate email
    if db.query(Student).filter(Student.email.ilike(signup_data.email)).first():
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    # 3. Check for duplicate university ID
    if db.query(Student).filter(Student.university_id == signup_data.university_id).first():
        raise HTTPException(status_code=400, detail="An account with this university ID already exists.")

    # 4. Validate password strength
    is_strong, msg = validate_password_strength(signup_data.password)
    if not is_strong:
        raise HTTPException(status_code=400, detail=msg)

    # 5. Validate grade values for completed courses
    for entry in signup_data.completed_courses:
        if entry.grade.upper() not in GRADE_POINTS:
            raise HTTPException(status_code=400, detail=f"Invalid grade '{entry.grade}' for course {entry.course_code}.")

    # 6. Calculate GPA from completed courses
    total_points = 0.0
    total_credits = 0.0
    completed_credit_count = 0
    for entry in signup_data.completed_courses:
        grade = entry.grade.upper()
        if grade not in GRADE_POINTS:
            continue
        course = db.query(Course).filter(Course.code == entry.course_code).first()
        if course and course.credit_hours:
            credits = float(course.credit_hours)
            total_points += GRADE_POINTS[grade] * credits
            total_credits += credits
            completed_credit_count += int(course.credit_hours)

    gpa = round(total_points / total_credits, 2) if total_credits > 0 else 0.0

    # 7. Determine academic standing from completed credits
    if completed_credit_count < 30:
        academic_standing = "first year"
    elif completed_credit_count < 60:
        academic_standing = "second year"
    elif completed_credit_count < 90:
        academic_standing = "third year"
    else:
        academic_standing = "fourth year"

    # Query all advisors from CsFacultyInfo and pick a random one
    import random
    from app.models.cs_faculty_info import CsFacultyInfo
    
    advisors = db.query(CsFacultyInfo).all()
    chosen_advisor_id = None
    if advisors:
        chosen_advisor_id = random.choice(advisors).email

    # 8. Create student record with hashed password
    student = Student(
        university_id=signup_data.university_id,
        email=signup_data.email.strip().lower(),
        first_name=signup_data.first_name.strip(),
        last_name=signup_data.last_name.strip(),
        password=pwd_context.hash(signup_data.password),
        phone_number=signup_data.phone_number.strip(),
        major="Computer Science",
        current_gpa=gpa,
        academic_standing=academic_standing,
        completed_credits=completed_credit_count,
        remaining_courses=len(signup_data.remaining_courses),
        advisor_id=chosen_advisor_id,
    )
    db.add(student)
    db.flush()

    # 9. Build roadmap entries for all curriculum courses
    completed_map = {e.course_code: e.grade.upper() for e in signup_data.completed_courses}
    enrolled_set = set(signup_data.current_enrolled)
    remaining_set = set(signup_data.remaining_courses)

    all_courses = db.query(Course).all()
    for course in all_courses:
        if course.code in completed_map:
            db.add(StudentRoadmap(
                student_id=signup_data.university_id,
                course_code=course.code,
                status="Completed",
                grade=completed_map[course.code],
                year=course.suggested_year,
                semester=course.suggested_semester,
            ))
        elif course.code in enrolled_set:
            db.add(StudentRoadmap(
                student_id=signup_data.university_id,
                course_code=course.code,
                status="Currently Enrolled",
                grade=None,
                year=course.suggested_year,
                semester=course.suggested_semester,
            ))
        elif course.code in remaining_set:
            db.add(StudentRoadmap(
                student_id=signup_data.university_id,
                course_code=course.code,
                status="Available",
                grade=None,
                year=course.suggested_year,
                semester=course.suggested_semester,
            ))
        else:
            db.add(StudentRoadmap(
                student_id=signup_data.university_id,
                course_code=course.code,
                status="locked",
                grade=None,
                year=course.suggested_year,
                semester=course.suggested_semester,
            ))

    db.commit()
    return {"message": "Account created successfully. You can now log in.", "student_id": signup_data.university_id}
