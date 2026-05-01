from fastapi import APIRouter, Depends, HTTPException, status,Form
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
def login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    student = db.query(Student).filter(Student.email == email).first()

    if not student or student.password != password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    return {"message": "Login successful", "student_id": student.university_id}


