from pydantic import BaseModel
from typing import Optional


# ── Request: Create a private study room ─────────────────────────
class CreateRoomRequest(BaseModel):
    name: str
    password: Optional[str] = None   # None = Public room


# ── Request: Join a private study room ───────────────────────────
class JoinRoomRequest(BaseModel):
    student_id: str
    password: Optional[str] = None


# ── Response: Study room info ─────────────────────────────────────
class RoomResponse(BaseModel):
    id: int
    name: str
    type: str            # "Public" or "Private"
    creator_id: str

    class Config:
        from_attributes = True


# ── Response: Official room info ──────────────────────────────────
class OfficialRoomResponse(BaseModel):
    id: int
    course_code: str
    type: str

    class Config:
        from_attributes = True


# ── Response: Room member ─────────────────────────────────────────
class RoomMemberResponse(BaseModel):
    student_id: str
    room_id: int
    room_type: str

    class Config:
        from_attributes = True
