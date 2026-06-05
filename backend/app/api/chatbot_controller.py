from fastapi import APIRouter, Depends, HTTPException, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.ai_advisor import get_advisor
from app.models.chatbot_history import ChatbotHistory
from app.models.student import Student

router = APIRouter(prefix="/chat", tags=["Chatbot"])

DEMO_RESPONSES = [
    "I'm your AI Academic Advisor at JUST! To enable full AI capabilities with RAG "
    "(Retrieval-Augmented Generation), please configure GEMINI_API_KEY and "
    "PINECONE_API_KEY in your environment. Once configured, I can answer questions "
    "about courses, prerequisites, graduation requirements, and more using official "
    "JUST CS department data.",
    "The CS degree at JUST requires 132 credit hours. You'll cover foundational "
    "courses in Year 1-2, advanced CS topics in Year 3, and the Graduation Project "
    "in Year 4. Check your roadmap page for your personal progress.",
]
_demo_counter = 0


# ── Schemas ───────────────────────────────────────────────────────────────────

class AiChatRequest(BaseModel):
    student_id: str
    question: str


def _can_persist_history(student_id: str, db: Session) -> bool:
    if not student_id or student_id == "guest":
        return False
    return db.query(Student).filter(Student.university_id == student_id).first() is not None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/history/{student_id}")
def get_chat_history(student_id: str, db: Session = Depends(get_db)):
    if not _can_persist_history(student_id, db):
        return []

    history = (
        db.query(ChatbotHistory)
        .filter(ChatbotHistory.student_id == student_id)
        .order_by(ChatbotHistory.timestamp.asc())
        .all()
    )
    return [
        {
            "id": msg.id,
            "message_content": msg.message_content,
            "sender_type": msg.sender_type,
            "source": msg.source,
            "timestamp": msg.timestamp,
        }
        for msg in history
    ]


@router.post("/ai")
def ai_chat(req: AiChatRequest, db: Session = Depends(get_db)):
    """
    Hybrid RAG endpoint.

    Flow:
      1. Save the user's question to chat history (logged-in students only).
      2. Run HybridAdvisorChain (Pinecone → threshold → Gemini).
      3. Save the bot answer with its source tag.
      4. Return { answer, source, confidence }.

    If API keys are not configured the endpoint returns a helpful demo answer
    so the UI remains functional during local development.
    """
    global _demo_counter

    persist = _can_persist_history(req.student_id, db)

    if persist:
        db.add(ChatbotHistory(
            student_id=req.student_id,
            message_content=req.question,
            sender_type="user",
            source=None,
        ))
        db.flush()

    advisor = get_advisor()
    if advisor is None:
        answer = DEMO_RESPONSES[_demo_counter % len(DEMO_RESPONSES)]
        _demo_counter += 1
        source = "demo"
        confidence = 0.0
    else:
        try:
            result = advisor.query(req.question)
            answer = result["answer"]
            source = result["source"]
            confidence = result["confidence"]
        except Exception as exc:
            err_str = str(exc).lower()
            if "api key" in err_str or "invalid_argument" in err_str or "expired" in err_str or "quota" in err_str:
                answer = (
                    "The AI service is temporarily unavailable — the API key may have expired or exceeded its quota. "
                    "Please contact the administrator to renew the key. "
                    "In the meantime, you can browse your Course Roadmap, GPA Calculator, and Study Rooms."
                )
                source = "error"
                confidence = 0.0
            else:
                if persist:
                    db.rollback()
                raise HTTPException(status_code=503, detail="AI service is currently unavailable. Please try again later.")

    if persist:
        db.add(ChatbotHistory(
            student_id=req.student_id,
            message_content=answer,
            sender_type="bot",
            source=source,
        ))
        db.commit()

    return {"answer": answer, "source": source, "confidence": confidence}


@router.post("/message")
def save_chat_message(
    student_id: str = Form(...),
    message_content: str = Form(...),
    sender_type: str = Form(default="user"),
    db: Session = Depends(get_db)
):
    """Legacy endpoint kept for backward compatibility."""
    if sender_type not in ("user", "bot"):
        sender_type = "user"
    if not _can_persist_history(student_id, db):
        return {"message": "Message not saved (guest or unknown student)"}
    db.add(ChatbotHistory(
        student_id=student_id,
        message_content=message_content,
        sender_type=sender_type,
    ))
    db.commit()
    return {"message": "Message saved successfully"}
