from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.constants import GRADE_POINTS
from app.models.student_roadmap import StudentRoadmap
from app.models.course import Course

router = APIRouter(prefix="/roadmap", tags=["Roadmap"])

@router.get("/{student_id}")
def get_roadmap(student_id: str, db: Session = Depends(get_db)):
    roadmap_items = db.query(StudentRoadmap).filter(StudentRoadmap.student_id == student_id)\
        .order_by(StudentRoadmap.year, StudentRoadmap.semester.desc()).all()
    if not roadmap_items:
        return []

    seen_codes = set()
    result = []
    for item in roadmap_items:
        if item.course_code in seen_codes:
            continue
        seen_codes.add(item.course_code)
        course = db.query(Course).filter(Course.code == item.course_code).first()
        if course:
            result.append({
                "course_code": item.course_code,
                "course_name": course.name,
                "credit_hours": course.credit_hours,
                "status": item.status,
                "grade": item.grade,
                "suggested_year": course.suggested_year,
                "suggested_semester": course.suggested_semester,
                "prerequisites": course.prerequisites,
                "year": item.year,
                "semester": item.semester,
            })
    return result

@router.get("/{student_id}/recalculate-gpa")
def recalculate_gpa(student_id: str, db: Session = Depends(get_db)):
    from app.models.student import Student

    student = db.query(Student).filter(Student.university_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    roadmap_items = db.query(StudentRoadmap).filter(
        StudentRoadmap.student_id == student_id
    ).all()

    total_points = 0.0
    total_credits = 0.0

    for item in roadmap_items:
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

    gpa = round(total_points / total_credits, 2) if total_credits > 0 else 0.0
    student.current_gpa = gpa
    db.commit()

    return {"gpa": gpa, "total_credits": total_credits}

@router.get("/{student_id}/sync-stats")
def sync_roadmap_stats(student_id: str, db: Session = Depends(get_db)):
    from app.models.student import Student

    student = db.query(Student).filter(Student.university_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    roadmap_items = db.query(StudentRoadmap).filter(StudentRoadmap.student_id == student_id).all()

    completed_credits = 0
    remaining_credits = 0

    for item in roadmap_items:
        course = db.query(Course).filter(Course.code == item.course_code).first()
        if not course:
            continue

        status = (item.status or "").lower()
        if status == "completed":
            completed_credits += int(course.credit_hours or 0)
        elif status in ["available", "locked"]:
            remaining_credits += int(course.credit_hours or 0)

    student.completed_credits = completed_credits
    student.remaining_courses = remaining_credits
    db.commit()
    db.refresh(student)

    return {
        "completed_credits": completed_credits,
        "remaining_credits": remaining_credits
    }
