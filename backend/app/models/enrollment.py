from sqlalchemy import Column, Integer, String, Float, ForeignKey
from app.core.database import Base


class Enrollment(Base):
    __tablename__ = "enrollment"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(String, ForeignKey("students.university_id"), nullable=False)
    course_code = Column(String, ForeignKey("courses.code"), nullable=False)
    semester = Column(String)
    grade = Column(Float, nullable=True)
    status = Column(String) # "Enrolled/Completed"
