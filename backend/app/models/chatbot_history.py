from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class ChatbotHistory(Base):
    __tablename__ = "chatbot_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(String, ForeignKey("students.university_id"), nullable=False)
    message_content = Column(Text, nullable=False)
    sender_type = Column(String, default="user")  # "user" or "bot"
    # "official" = grounded in JUST CS knowledge base
    # "general"  = Groq general-knowledge answer
    # "demo"     = demo mode (no API key)
    # "error"    = AI service error
    # None       = legacy messages or user messages
    source = Column(String, nullable=True)
    # Confidence score (0.0 to 1.0) for official source classification
    confidence = Column(Float, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
