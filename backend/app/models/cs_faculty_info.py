from sqlalchemy import Column, String
from app.core.database import Base

class CsFacultyInfo(Base):
    __tablename__ = "cs_faculty_info"
    # الإيميل هو المفتاح الأساسي (يمنع التكرار تماماً)
    email = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    office_location = Column(String)
    office_hours = Column(String)