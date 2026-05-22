from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Student(Base):
    __tablename__ = "students"
    university_id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    password = Column(String)
    phone_number = Column(String)
    major = Column(String, nullable=True)
    current_gpa = Column(Float, nullable=True)
    academic_standing = Column(String)
    completed_credits = Column(Integer, default=0)
    remaining_courses = Column(Integer, default=0)
    advisor_id = Column(String, ForeignKey("cs_faculty_info.email"), nullable=True)

    advisor = relationship("CsFacultyInfo")