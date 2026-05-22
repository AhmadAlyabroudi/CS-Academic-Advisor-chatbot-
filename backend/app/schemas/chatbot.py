from pydantic import BaseModel
from typing import Optional


# ── Request: Send a chat message ─────────────────────────────────
class ChatMessageRequest(BaseModel):
    student_id: str
    message: str
    session_id: Optional[str] = None  # For grouping conversations


# ── Response: Chatbot reply ───────────────────────────────────────
class ChatMessageResponse(BaseModel):
    student_id: str
    user_message: str
    bot_response: str
    session_id: Optional[str] = None

    class Config:
        from_attributes = True


# ── Response: Chat history entry ──────────────────────────────────
class ChatHistoryResponse(BaseModel):
    id: int
    student_id: str
    user_message: str
    bot_response: str

    class Config:
        from_attributes = True
