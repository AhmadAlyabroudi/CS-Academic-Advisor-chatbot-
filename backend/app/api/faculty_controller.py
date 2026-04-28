from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.cs_faculty_info import CsFacultyInfo
from app.schemas.cs_faculty_info import FacultySchema

router = APIRouter()


@router.get("/faculty", tags=["Faculty"], response_model=list[FacultySchema])
def get_all_faculty(db: Session = Depends(get_db)):
    """
    Returns faculty info: name, email, office location, and office hours.
    """
    faculty_data = db.query(CsFacultyInfo).all()

    return faculty_data
