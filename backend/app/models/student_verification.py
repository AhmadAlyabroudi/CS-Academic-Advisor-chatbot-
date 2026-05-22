from sqlalchemy import Column, Integer, String
from app.core.database import Base


class StudentVerification(Base):
    __tablename__ = "student_verification"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False, index=True)
    university_id = Column(String, unique=True, nullable=False, index=True)
