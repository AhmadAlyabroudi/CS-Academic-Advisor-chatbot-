from sqlalchemy import Column, Integer, String, ForeignKey
from app.core.database import Base


class StudentRoadmap(Base):
    __tablename__ = "student_roadmap"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(String, ForeignKey("students.university_id"), nullable=False)
    course_code = Column(String, ForeignKey("courses.code"), nullable=False)
    status = Column(String) # "Locked/Available/Currently Enrolled/Completed"
    grade = Column(String, nullable=True)  # e.g. "A+", "B", "C-", null if not completed
    year = Column(Integer)  # 1, 2, 3, 4
    semester = Column(String)  # "Fall" or "Spring"
