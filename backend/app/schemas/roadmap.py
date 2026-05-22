from pydantic import BaseModel
from typing import Optional


# ── Response: Single roadmap course entry ─────────────────────────
class RoadmapCourseResponse(BaseModel):
    course_code: str
    course_name: str
    credit_hours: int
    status: str                        # Completed / Currently Enrolled / Available / locked
    suggested_year: Optional[int] = None
    suggested_semester: Optional[str] = None
    prerequisites: Optional[str] = None
    year: Optional[int] = None         # Student's actual year placement
    semester: Optional[str] = None     # Student's actual semester placement

    class Config:
        from_attributes = True


# ── Response: Roadmap stats (sync-stats endpoint) ─────────────────
class RoadmapStatsResponse(BaseModel):
    completed_credits: int
    remaining_credits: int


# ── Request: Update a course status in a student's roadmap ────────
class RoadmapStatusUpdate(BaseModel):
    student_id: str
    course_code: str
    status: str   # "Completed" | "Currently Enrolled" | "Available" | "locked"
