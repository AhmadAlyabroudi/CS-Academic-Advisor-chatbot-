from pydantic import BaseModel, EmailStr
from typing import Optional, List


class StudentBase(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    academic_standing: Optional[str] = None

class StudentCreate(StudentBase):
    password: str

class StudentLogin(BaseModel):
    email: str
    password: str

class Student(StudentBase):
    id: int

    class Config:
        from_attributes = True

class StudentUpdate(BaseModel):
    first_name: str
    last_name: str
    phone_number: str

class StudentPasswordUpdate(BaseModel):
    current_password: str
    new_password: str

class CourseGradeEntry(BaseModel):
    course_code: str
    grade: str

class StudentSignup(BaseModel):
    first_name: str
    last_name: str
    email: str
    university_id: str
    phone_number: str
    password: str
    completed_courses: List[CourseGradeEntry] = []
    current_enrolled: List[str] = []
    remaining_courses: List[str] = []
