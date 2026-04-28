from pydantic import BaseModel, EmailStr
from typing import Optional

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
