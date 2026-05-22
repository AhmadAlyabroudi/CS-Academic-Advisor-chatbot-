from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from app.core.constants import GRADE_POINTS

router = APIRouter(prefix="/api", tags=["GPA"])

class CourseGrade(BaseModel):
    grade: str
    credit_hours: float

class GpaCalculationRequest(BaseModel):
    current_cgpa: float = 0.0
    current_completed_hours: float = 0.0
    courses: List[CourseGrade] = []

def calculate_semester_gpa(courses: List[CourseGrade]):
    semester_points = 0.0
    semester_hours = 0.0

    for c in courses:
        credits = c.credit_hours
        grade = str(c.grade).upper()

        if credits <= 0 or grade not in GRADE_POINTS:
            continue

        semester_hours += credits
        semester_points += credits * GRADE_POINTS[grade]

    gpa = semester_points / semester_hours if semester_hours > 0 else 0.0
    return round(gpa, 2), semester_points, semester_hours

def calculate_new_cgpa(current_cgpa, current_hours, semester_points, semester_hours):
    current_cgpa = float(current_cgpa or 0)
    current_hours = float(current_hours or 0)
    semester_points = float(semester_points or 0)
    semester_hours = float(semester_hours or 0)

    total_points_before = current_cgpa * current_hours
    total_points_after = total_points_before + semester_points
    total_hours_after = current_hours + semester_hours

    if total_hours_after <= 0:
        return round(current_cgpa, 2)

    return round(total_points_after / total_hours_after, 2)

@router.post("/calculate-gpa")
def calculate_gpa(data: GpaCalculationRequest):
    semester_gpa, semester_points, semester_hours = calculate_semester_gpa(data.courses)

    new_cgpa = calculate_new_cgpa(
        data.current_cgpa, data.current_completed_hours, semester_points, semester_hours
    )

    return {
        "semester_gpa": semester_gpa,
        "new_cgpa": new_cgpa,
        "semester_hours": semester_hours,
    }
