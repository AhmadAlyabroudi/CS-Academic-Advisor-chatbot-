"""
Chatbot REST API controller.

Endpoints:
  POST /chat/ai          — Main AI chat (with conversation memory)
  GET  /chat/history/{id} — Retrieve chat history for a student
  POST /chat/clear/{id}  — Clear chat history for a student
  POST /chat/message      — Legacy endpoint (backward compat)
"""

from fastapi import APIRouter, Depends, HTTPException, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.ai_advisor import get_advisor
from app.core.constants import GRADE_POINTS
from app.models.chatbot_history import ChatbotHistory
from app.models.student import Student
from app.models.student_roadmap import StudentRoadmap
from app.models.course import Course
from app.models.cs_faculty_info import CsFacultyInfo

router = APIRouter(prefix="/chat", tags=["Chatbot"])

# Maximum number of past messages to load as AI context
MAX_CONTEXT_MESSAGES = 20

DEMO_RESPONSES = [
    "I'm your AI Academic Advisor at JUST! To enable full AI capabilities, please "
    "configure **GROQ_API_KEY** in your environment.\n\n"
    "Once configured, I can answer questions about:\n"
    "- 📚 Course prerequisites and progression\n"
    "- 🎓 Graduation requirements (132 credit hours)\n"
    "- 📊 GPA calculation (4.2 scale)\n"
    "- 💼 Practical Training (CS391)\n"
    "- 🏗️ Graduation Projects (CS491/CS492)\n\n"
    "Check the **Course Roadmap** page for your personal progress!",

    "The CS degree at JUST requires **132 credit hours** distributed as:\n\n"
    "| Category | Hours |\n"
    "|----------|-------|\n"
    "| University Compulsory | 16 |\n"
    "| Faculty Compulsory | 30 |\n"
    "| Department Compulsory | 74 |\n"
    "| Department Elective | 9 |\n"
    "| University Elective | 9 |\n\n"
    "You'll cover foundational courses in **Year 1-2**, advanced CS topics in **Year 3**, "
    "and the **Graduation Project** in **Year 4**.",
]
_demo_counter = 0


# ── Schemas ───────────────────────────────────────────────────────────────────

class AiChatRequest(BaseModel):
    student_id: str
    question: str


def _can_persist_history(student_id: str, db: Session) -> bool:
    """Check if this student exists in the database for history persistence."""
    if not student_id or student_id == "guest":
        return False
    return db.query(Student).filter(Student.university_id == student_id).first() is not None


def _load_conversation_context(student_id: str, db: Session) -> list[dict]:
    """Load recent conversation messages from DB to use as AI context.

    Returns a list of {"role": "user"|"assistant", "content": "..."} dicts
    suitable for passing directly to the Groq API.
    """
    if not student_id or student_id == "guest":
        return []

    recent_messages = (
        db.query(ChatbotHistory)
        .filter(ChatbotHistory.student_id == student_id)
        .order_by(ChatbotHistory.timestamp.desc())
        .limit(MAX_CONTEXT_MESSAGES)
        .all()
    )

    # Reverse to get chronological order (oldest first)
    recent_messages.reverse()

    context = []
    for msg in recent_messages:
        role = "user" if msg.sender_type == "user" else "assistant"
        context.append({"role": role, "content": msg.message_content})

    return context


def _build_student_context(student_id: str, db: Session) -> str:
    """Build a structured text block with the student's full profile data.

    This context is injected into the AI system prompt so the chatbot can
    answer personalised questions (e.g. remaining hours, GPA, completed
    courses).  The student's **password is never included**.
    """
    if not student_id or student_id == "guest":
        return ""

    student = db.query(Student).filter(Student.university_id == student_id).first()
    if not student:
        return ""

    # ── Basic profile ─────────────────────────────────────────────────────
    lines: list[str] = [
        f"Student Name: {student.first_name or ''} {student.last_name or ''}",
        f"University ID: {student.university_id}",
        f"Email: {student.email or 'N/A'}",
        f"Phone: {student.phone_number or 'N/A'}",
        f"Major: {student.major or 'Computer Science'}",
        f"Academic Standing: {student.academic_standing or 'N/A'}",
    ]

    # ── Advisor info ──────────────────────────────────────────────────────
    if student.advisor_id:
        advisor = db.query(CsFacultyInfo).filter(CsFacultyInfo.email == student.advisor_id).first()
        if advisor:
            lines.append(f"Academic Advisor: {advisor.name} ({advisor.email}), Office: {advisor.office_location}, Hours: {advisor.office_hours}")

    # ── Roadmap analysis ──────────────────────────────────────────────────
    roadmap_items = (
        db.query(StudentRoadmap)
        .filter(StudentRoadmap.student_id == student_id)
        .all()
    )

    completed_courses: list[str] = []
    enrolled_courses: list[str] = []
    remaining_courses: list[str] = []
    total_completed_credits = 0
    total_points = 0.0

    for item in roadmap_items:
        course = db.query(Course).filter(Course.code == item.course_code).first()
        credit_hours = course.credit_hours if course else 0
        status = (item.status or "").lower()

        if status == "completed":
            grade_str = (item.grade or "").upper()
            completed_courses.append(f"{item.course_code}:{grade_str or 'N/A'}")
            total_completed_credits += credit_hours
            if grade_str in GRADE_POINTS and credit_hours:
                total_points += GRADE_POINTS[grade_str] * float(credit_hours)
        elif status in ("currently enrolled", "enrolled"):
            enrolled_courses.append(item.course_code)
        else:
            remaining_courses.append(item.course_code)

    total_required_credits = 132
    remaining_credits = total_required_credits - total_completed_credits
    computed_gpa = round(total_points / total_completed_credits, 2) if total_completed_credits > 0 else 0.0
    current_gpa = student.current_gpa if student.current_gpa is not None else computed_gpa

    lines.append(f"Current GPA: {current_gpa}")
    lines.append(f"Completed Credits: {total_completed_credits} / {total_required_credits}")
    lines.append(f"Remaining Credits: {remaining_credits}")
    lines.append(f"Completed Courses: {', '.join(completed_courses)}")
    lines.append(f"Currently Enrolled: {', '.join(enrolled_courses)}")
    lines.append(f"Remaining Courses: {', '.join(remaining_courses)}")

    return "\n".join(lines)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/history/{student_id}")
def get_chat_history(student_id: str, db: Session = Depends(get_db)):
    """Retrieve full chat history for a student."""
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
            "confidence": msg.confidence,
            "timestamp": msg.timestamp,
        }
        for msg in history
    ]


@router.post("/ai")
def ai_chat(req: AiChatRequest, db: Session = Depends(get_db)):
    """Groq-backed chat endpoint with conversation memory.

    Flow:
      1. Load recent conversation history from the database.
      2. Save the user's question to chat history (logged-in students only).
      3. Run GroqAdvisorChain with conversation context.
      4. Save the bot answer with its source tag and confidence.
      5. Return { answer, source, confidence }.
    """
    global _demo_counter

    persist = _can_persist_history(req.student_id, db)

    # Load conversation context BEFORE saving the new message
    # (so we don't include the current question twice)
    conversation_history = _load_conversation_context(req.student_id, db) if persist else []

    # Build personalised student context (everything except password)
    student_context = _build_student_context(req.student_id, db)

    # Save user message
    if persist:
        db.add(ChatbotHistory(
            student_id=req.student_id,
            message_content=req.question,
            sender_type="user",
            source=None,
            confidence=None,
        ))
        db.flush()

    # Get AI response
    advisor = get_advisor()
    if advisor is None:
        # Demo mode — no API key configured
        answer = DEMO_RESPONSES[_demo_counter % len(DEMO_RESPONSES)]
        _demo_counter += 1
        source = "demo"
        confidence = 0.0
    else:
        try:
            result = advisor.query(
                question=req.question,
                history=conversation_history,
                student_context=student_context,
            )
            answer = result["answer"]
            source = result["source"]
            confidence = result["confidence"]
        except Exception as exc:
            import traceback
            answer = f"⚠️ **AI Service Temporarily Unavailable**\n\nException: {str(exc)}\n\nTraceback:\n{traceback.format_exc()}"
            source = "error"
            confidence = 0.0

    # Save bot response
    if persist:
        db.add(ChatbotHistory(
            student_id=req.student_id,
            message_content=answer,
            sender_type="bot",
            source=source,
            confidence=confidence,
        ))
        db.commit()

    return {"answer": answer, "source": source, "confidence": confidence}


@router.post("/clear/{student_id}")
def clear_chat_history(student_id: str, db: Session = Depends(get_db)):
    """Clear all chat history for a student."""
    if not _can_persist_history(student_id, db):
        return {"message": "No history to clear"}

    deleted = (
        db.query(ChatbotHistory)
        .filter(ChatbotHistory.student_id == student_id)
        .delete()
    )
    db.commit()
    return {"message": f"Cleared {deleted} messages"}


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
