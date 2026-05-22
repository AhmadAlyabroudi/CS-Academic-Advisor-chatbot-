from sqlalchemy import Column, String, ForeignKey, Integer
from app.core.database import Base


class Course(Base):
    __tablename__ = "courses"

    code = Column(String, primary_key=True, index=True)
    id_reg = Column(String, nullable=True)    # University registration ID
    name = Column(String, nullable=False)
    prerequisites = Column(String, nullable=True)
    plan_type = Column(String)
    credit_hours = Column(Integer)
    suggested_year = Column(Integer)      # 1, 2, 3, 4
    suggested_semester = Column(String)   # "Fall" or "Spring"