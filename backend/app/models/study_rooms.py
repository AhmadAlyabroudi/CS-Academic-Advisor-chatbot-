from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class OfficialRooms(Base):
    __tablename__ = "official_rooms"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    course_code = Column(String, ForeignKey("courses.code"), nullable=False)
    type = Column(String, default="Official")


class PrivateStudyRooms(Base):
    __tablename__ = "private_study_rooms"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    creator_id = Column(String, ForeignKey("students.university_id"), nullable=False)
    name = Column(String, nullable=False)
    password = Column(String, nullable=True)
    type = Column(String, default="Public") # "Public/Private"


class RoomMembers(Base):
    __tablename__ = "room_members"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    room_id = Column(Integer, nullable=False) # Can reference both official and private
    room_type = Column(String, nullable=False) # "Official" or "Private"
    student_id = Column(String, ForeignKey("students.university_id"), nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
