from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.student import Student
from app.schemas.student import StudentLogin

router = APIRouter()

@router.get("/students", tags=["Students"])
def get_students(db: Session = Depends(get_db)):
    """
    Returns all students from the database.
    """
    students = db.query(Student).all()

    return students

@router.post("/login", tags=["Authentication"])
def login(student_login: StudentLogin, db: Session = Depends(get_db)):
    """
    Simple student login endpoint.
    """
    student = db.query(Student).filter(Student.email == student_login.email).first()

# TODO:  Compared hashed passwords instead of plain strings. Hint: Apply it on seeding first so u can test it.
    if not student or student.password != student_login.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    return {"message": "Login successful", "student_id": student.id}


