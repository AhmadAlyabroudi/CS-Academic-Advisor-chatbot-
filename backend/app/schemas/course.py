from pydantic import BaseModel
from typing import Optional


# ── Response: Single course ───────────────────────────────────────
class CourseResponse(BaseModel):
    code: str
    id_reg: Optional[str] = None
    name: str
    prerequisites: Optional[str] = None
    plan_type: Optional[str] = None
    credit_hours: int
    suggested_year: Optional[int] = None
    suggested_semester: Optional[str] = None

    class Config:
        from_attributes = True
