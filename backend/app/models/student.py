from sqlalchemy import Column, Integer, String
from app.core.database import Base


class Student(Base):
    __tablename__ = "students"
    university_id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    password = Column(String)
    phone_number = Column(String)
    academic_standing = Column(String)