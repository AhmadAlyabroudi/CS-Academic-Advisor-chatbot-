from sqlalchemy import Column, String, ForeignKey
from app.core.database import Base


class Course(Base):
    __tablename__ = "courses"

    code = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    prerequisites = Column(String, nullable=True)
    plan_type = Column(String)
    credit_hours = Column(String)
    year_and_semester = Column(String)