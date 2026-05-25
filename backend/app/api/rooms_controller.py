from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import os
from livekit.api import AccessToken, VideoGrants
from app.core.database import get_db
from app.models.study_rooms import OfficialRooms, PrivateStudyRooms, RoomMembers
from app.models.student import Student
from app.models.course import Course
from app.models.student_roadmap import StudentRoadmap

router = APIRouter(prefix="/rooms", tags=["Study Rooms"])

@router.get("/")
def get_all_rooms(student_id: Optional[str] = None, db: Session = Depends(get_db)):
    # 1. Official Rooms filtered by student's current enrollment
    enrolled_courses = []
    if student_id:
        enrolled_courses = db.query(StudentRoadmap.course_code).filter(
            StudentRoadmap.student_id == student_id,
            StudentRoadmap.status == "Currently Enrolled"
        ).all()
        enrolled_courses = [c[0] for c in enrolled_courses]

    official_rooms = db.query(OfficialRooms).filter(OfficialRooms.course_code.in_(enrolled_courses)).all() if enrolled_courses else []
    
    # 2. User Created Rooms (Show all as requested)
    private_rooms = db.query(PrivateStudyRooms).all()

    rooms_response = []
    for room in official_rooms:
        course = db.query(Course).filter(Course.code == room.course_code).first()
        rooms_response.append({
            "id": room.id,
            "name": f"Official: {course.name if course else room.course_code}",
            "type": "Official",
            "course_code": room.course_code,
            "creator_id": "System"
        })

    for room in private_rooms:
        student = db.query(Student).filter(Student.university_id == room.creator_id).first()
        creator_name = f"{student.first_name} {student.last_name}" if student else room.creator_id
        
        rooms_response.append({
            "id": room.id,
            "name": room.name,
            "type": "Private",
            "creator_id": room.creator_id,
            "creator_name": creator_name,
            "room_privacy": room.type # "Public" or "Private"
        })

    return rooms_response

@router.get("/{room_type}/{room_id}")
def get_room_details(room_type: str, room_id: int, db: Session = Depends(get_db)):
    if room_type == "Official":
        room = db.query(OfficialRooms).filter(OfficialRooms.id == room_id).first()
        if not room: raise HTTPException(status_code=404, detail="Room not found")
        course = db.query(Course).filter(Course.code == room.course_code).first()
        return {
            "id": room.id,
            "name": f"Official: {course.name if course else room.course_code}",
            "type": "Official",
            "creator_id": "System"
        }
    else:
        room = db.query(PrivateStudyRooms).filter(PrivateStudyRooms.id == room_id).first()
        if not room: raise HTTPException(status_code=404, detail="Room not found")
        student = db.query(Student).filter(Student.university_id == room.creator_id).first()
        creator_name = f"{student.first_name} {student.last_name}" if student else room.creator_id
        return {
            "id": room.id,
            "name": room.name,
            "type": "Private",
            "creator_id": room.creator_id,
            "creator_name": creator_name
        }

@router.post("/create")
def create_room(
    name: str = Form(...),
    type: str = Form(...), # "Public" or "Private"
    creator_id: str = Form(...),
    password: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    new_room = PrivateStudyRooms(
        name=name,
        type=type,
        creator_id=creator_id,
        password=password
    )
    db.add(new_room)
    db.commit()
    db.refresh(new_room)
    return {"message": "Room created successfully", "room_id": new_room.id}

@router.post("/join")
def join_room(
    room_id: int = Form(...),
    room_type: str = Form(...), 
    student_id: str = Form(...),
    db: Session = Depends(get_db)
):
    # Check if already joined
    existing_member = db.query(RoomMembers).filter(
        RoomMembers.room_id == room_id,
        RoomMembers.room_type == room_type,
        RoomMembers.student_id == student_id
    ).first()

    if existing_member:
        return {"message": "Already joined this room"}

    new_member = RoomMembers(
        room_id=room_id,
        room_type=room_type,
        student_id=student_id
    )
    db.add(new_member)
    db.commit()

    return {"message": "Successfully joined the room"}

@router.post("/leave")
def leave_room(
    room_id: int = Form(...),
    room_type: str = Form(...),
    student_id: str = Form(...),
    db: Session = Depends(get_db)
):
    member = db.query(RoomMembers).filter(
        RoomMembers.room_id == room_id,
        RoomMembers.room_type == room_type,
        RoomMembers.student_id == student_id
    ).first()
    
    if member:
        db.delete(member)
        db.commit()
    return {"message": "Left room"}

@router.delete("/{room_type}/{room_id}")
def terminate_room(
    room_type: str,
    room_id: int,
    student_id: str,
    db: Session = Depends(get_db)
):
    if room_type == "Official":
        raise HTTPException(status_code=403, detail="Cannot terminate official rooms")
    
    room = db.query(PrivateStudyRooms).filter(PrivateStudyRooms.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if room.creator_id != student_id:
        raise HTTPException(status_code=403, detail="Only creator can terminate room")

    # Remove all members first
    db.query(RoomMembers).filter(
        RoomMembers.room_id == room_id,
        RoomMembers.room_type == "Private"
    ).delete()
    
    db.delete(room)
    db.commit()
    return {"message": "Room terminated and all members removed"}




@router.get("/token")
def get_livekit_access_token(room_id: str, student_id: str, name: str):
    """
    توليد توكن دخول آمن ومشفر لكل طالب للغرفة عبر سيرفر الـ SFU
    """
    # جلب مفاتيح التشفير السرية المثبتة بملف الـ .env بالسيرفر
    api_key = os.getenv("LIVEKIT_API_KEY", "devkey")
    api_secret = os.getenv("LIVEKIT_API_SECRET", "secret")

    if not room_id or not student_id:
        raise HTTPException(status_code=400, detail="Missing parameters")

    # صياغة التصاريح الرسمية للبث (دخول الغرفة، تفعيل المايك والكاميرا)
        # صياغة التصاريح الرسمية للبث (دخول الغرفة، تفعيل المايك والكاميرا)
        grant = AccessToken(api_key, api_secret) \
            .with_identity(student_id) \
            .with_name(name) \
            .with_grants(VideoGrants(room_join=True, room=room_id))

    return {"token": grant.to_jwt()}