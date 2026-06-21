from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.core.constants import GRADE_POINTS
from app.models.student_roadmap import StudentRoadmap
from app.models.course import Course

router = APIRouter(prefix="/roadmap", tags=["Roadmap"])

class UpdateCourseRoadmapRequest(BaseModel):
    course_code: str
    status: str
    grade: Optional[str] = None

@router.post("/{student_id}/update-course")
def update_course_roadmap(student_id: str, payload: UpdateCourseRoadmapRequest, db: Session = Depends(get_db)):
    from app.models.student import Student

    student = db.query(Student).filter(Student.university_id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # 1. Normalize and validate inputs
    status_input = payload.status.strip()
    valid_statuses = ["Completed", "Currently Enrolled", "Available", "locked"]
    matched_status = None
    for vs in valid_statuses:
        if vs.lower() == status_input.lower():
            matched_status = vs
            break

    if not matched_status:
        raise HTTPException(status_code=400, detail=f"Invalid status '{payload.status}'. Must be one of {valid_statuses}")

    grade_input = None
    if matched_status == "Completed":
        if not payload.grade:
            raise HTTPException(status_code=400, detail="Grade is required when status is Completed.")
        grade_input = payload.grade.strip().upper()
        if grade_input not in GRADE_POINTS:
            raise HTTPException(status_code=400, detail=f"Invalid grade '{payload.grade}'. Must be one of {list(GRADE_POINTS.keys())}")
    else:
        grade_input = None

    # 2. Update the target course roadmap item
    target_item = db.query(StudentRoadmap).filter(
        StudentRoadmap.student_id == student_id,
        StudentRoadmap.course_code == payload.course_code
    ).first()

    if not target_item:
        course_info = db.query(Course).filter(Course.code == payload.course_code).first()
        if not course_info:
            raise HTTPException(status_code=404, detail="Course not found in catalog")
        target_item = StudentRoadmap(
            student_id=student_id,
            course_code=payload.course_code,
            status=matched_status,
            grade=grade_input,
            year=course_info.suggested_year,
            semester=course_info.suggested_semester
        )
        db.add(target_item)
    else:
        target_item.status = matched_status
        target_item.grade = grade_input

    db.flush()

    # 3. Dynamic locks/unlocks recalculation based on prerequisites
    all_roadmap = db.query(StudentRoadmap).filter(StudentRoadmap.student_id == student_id).all()
    all_courses = db.query(Course).all()
    
    course_map = {c.code: c for c in all_courses}

    # Normalize helpers
    def normalize_code(code: str) -> str:
        return code.strip().replace(" ", "").upper()

    # Calculate completed credits for PASS 90 check, and build completed/enrolled sets
    completed_credits = 0
    completed_or_enrolled_set = set()
    for item in all_roadmap:
        # Credits are only counted for completed courses
        if item.status == "Completed":
            c_info = course_map.get(item.course_code)
            if c_info:
                completed_credits += int(c_info.credit_hours or 0)
        
        # Prerequisite validation accepts both Completed and Currently Enrolled
        if item.status in ("Completed", "Currently Enrolled"):
            completed_or_enrolled_set.add(normalize_code(item.course_code))

    # Prerequisite verification helper
    def is_prereq_satisfied(prereq_str: str) -> bool:
        if not prereq_str or prereq_str.strip().lower() in ("none", "none "):
            return True
        if "PASS 90 Credit" in prereq_str:
            return completed_credits >= 90
        
        parts = prereq_str.split("&")
        for part in parts:
            if normalize_code(part) not in completed_or_enrolled_set:
                return False
        return True

    # Re-evaluate remaining locked/available items
    for item in all_roadmap:
        if item.status in ["Completed", "Currently Enrolled"]:
            continue
        
        c_info = course_map.get(item.course_code)
        if not c_info:
            continue

        if is_prereq_satisfied(c_info.prerequisites):
            item.status = "Available"
        else:
            item.status = "locked"

    db.commit()

    # 4. Synchronize stats and GPA
    recalculate_gpa(student_id, db)
    sync_roadmap_stats(student_id, db)

    return {"message": "Roadmap and student stats updated successfully"}

@router.get("/{student_id}")
def get_roadmap(student_id: str, db: Session = Depends(get_db)):
    roadmap_items = db.query(StudentRoadmap).filter(StudentRoadmap.student_id == student_id)\
        .order_by(StudentRoadmap.year, StudentRoadmap.semester.desc()).all()
    if not roadmap_items:
        return []

    result = []
    for item in roadmap_items:
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
