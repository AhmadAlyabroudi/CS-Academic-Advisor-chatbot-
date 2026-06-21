"""
AI Academic Advisor — Groq-powered chatbot with conversation memory.

This module provides the core AI logic for the JUST CS Academic Advisor:
  • Loads the official knowledge base (curriculum + regulations) into the system prompt.
  • Maintains conversation context by accepting message history.
  • Classifies answers as "official" (grounded in JUST data) or "general" (AI knowledge).
  • Uses Groq's Llama 3.3 70B model for high-quality responses.
"""

import os
import re
import logging
from typing import Optional, Protocol
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"
load_dotenv(BASE_DIR / ".env")# ── Model configuration ──────────────────────────────────────────────────────
GEMINI_MODEL = "gemini-1.5-flash"
GEMINI_TEMPERATURE = 0.3
GEMINI_MAX_TOKENS = 1200
MAX_HISTORY_MESSAGES = 6       # Max previous messages to include as context

# Heuristic threshold for classifying answers as official vs general
OFFICIAL_OVERLAP_THRESHOLD = 0.30

# ── System prompt ─────────────────────────────────────────────────────────────
JUST_ADVISOR_SYSTEM = """\
You are the **official AI Academic Advisor** for the Computer Science department \
at **Jordan University of Science and Technology (JUST)**.

## CRITICAL Language Rules
1. You MUST ONLY respond in **Arabic** or **English**. NEVER respond in Chinese, French, \
German, or any other language.
2. Detect the student's language from their message:
   - If the student writes in Arabic → respond entirely in Arabic.
   - If the student writes in English → respond entirely in English.
3. If the conversation started in Arabic, continue in Arabic unless the student explicitly \
switches to English (and vice versa).
4. If you cannot determine the language, default to English.

## Your Capabilities
- Course prerequisites and progression chains
- Graduation requirements (132 credit hours total)
- GPA calculation (JUST uses a 4.2 scale)
- Practical Training (CS391) eligibility and requirements
- Graduation Projects (CS491 / CS492) guidelines
- Academic standing, probation policies, and registration rules
- Faculty directory and contact information
- General CS academic guidance
- **Personalized advice based on the student's own profile data** (courses completed, \
GPA, remaining hours, enrolled courses, etc.)

## Response Guidelines
1. **Always respond in the same language the student uses** (Arabic or English ONLY).
2. **Use Markdown formatting** to make answers clear and scannable:
   - Use **bold** for course codes, important terms, and key numbers.
   - Use bullet points and numbered lists for multi-part answers.
   - Use headings (##) to organize long answers.
   - Use tables when comparing courses or listing multiple items.
   - Use `code style` for course codes when inline.
3. **Be specific** — always cite course codes (e.g., **CS284**), credit hours, and prerequisites.
4. **Be conversational and friendly** — you are a helpful advisor, not a bureaucratic system.
5. **Remember context** — reference earlier parts of the conversation when relevant.
6. **When the student asks about their own data** (GPA, remaining hours, completed courses, \
etc.), use the Student Profile data provided below to give accurate, personalized answers.
7. **When unsure**, clearly state that the student should verify with the CS department office.
8. **Prioritize official JUST CS data** provided below. If the data doesn't cover the question, \
use general CS knowledge and note that the student should confirm with the department.

## Official JUST CS Department Data
--- BEGIN OFFICIAL DATA ---
{knowledge_base}
--- END OFFICIAL DATA ---
"""

# Stop-words ignored when computing keyword overlap with the knowledge base.
_STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "of", "to", "in", "on", "for", "with", "by", "at", "from", "as",
    "and", "or", "but", "if", "then", "than", "that", "this", "these", "those",
    "i", "you", "he", "she", "we", "they", "it", "me", "us", "them",
    "my", "your", "our", "their", "his", "her", "its",
    "do", "does", "did", "can", "could", "should", "would", "will", "shall", "may", "might",
    "have", "has", "had", "how", "what", "when", "where", "why", "who", "which",
    "about", "into", "out", "up", "down", "over", "under", "again", "more", "most",
    "any", "some", "all", "no", "not", "so", "too", "very", "just",
    # Arabic stop words
    "ما", "هل", "من", "في", "على", "إلى", "عن", "مع", "هو", "هي",
    "أنا", "أنت", "نحن", "هم", "هذا", "هذه", "ذلك", "تلك",
    "كيف", "ماذا", "متى", "أين", "لماذا", "كم", "أي",
    "و", "أو", "لكن", "إذا", "ثم", "حتى",
}


class AdvisorChain(Protocol):
    """Protocol for advisor implementations."""
    def query(self, question: str, history: list[dict] | None = None, student_context: str | None = None) -> dict: ...


def _load_knowledge_base() -> str:
    """Concatenate every .txt file in knowledge_base/ into one block."""
    if not KNOWLEDGE_BASE_DIR.is_dir():
        return ""
    parts: list[str] = []
    for path in sorted(KNOWLEDGE_BASE_DIR.glob("*.txt")):
        try:
            parts.append(path.read_text(encoding="utf-8"))
        except OSError as exc:
            logger.warning("Could not read knowledge base file %s: %s", path, exc)
    return "\n\n".join(parts)


def _tokenize(text: str) -> set[str]:
    """Extract meaningful tokens from text for overlap scoring."""
    return {
        tok for tok in re.findall(r"[a-z0-9\u0600-\u06FF]+", text.lower())
        if len(tok) > 2 and tok not in _STOP_WORDS
    }


class GeminiAdvisorChain:
    """Gemini-backed academic advisor with conversation memory.

    The full knowledge base is included in the system prompt. For each
    question we compute a keyword-overlap score against the knowledge base
    to classify the answer source.
    """

    def __init__(self, gemini_key: str) -> None:
        import google.generativeai as genai

        genai.configure(api_key=gemini_key)
        self.knowledge_base = _load_knowledge_base()
        self.kb_tokens = _tokenize(self.knowledge_base)

        # Build the system prompt with knowledge base injected
        self.system_prompt = JUST_ADVISOR_SYSTEM.format(
            knowledge_base=self.knowledge_base if self.knowledge_base else "(No knowledge base loaded)"
        )

        logger.info(
            "GeminiAdvisorChain initialised (model=%s, kb=%d chars, %d tokens)",
            GEMINI_MODEL,
            len(self.knowledge_base),
            len(self.kb_tokens),
        )

    def _classify(self, question: str) -> tuple[str, float]:
        """Classify whether the question relates to official JUST data."""
        if not self.kb_tokens:
            return "general", 0.0
        q_tokens = _tokenize(question)
        if not q_tokens:
            return "general", 0.0
        overlap = len(q_tokens & self.kb_tokens) / len(q_tokens)
        source = "official" if overlap >= OFFICIAL_OVERLAP_THRESHOLD else "general"
        return source, round(overlap, 3)

    def query(self, question: str, history: list[dict] | None = None, student_context: str | None = None) -> dict:
        import google.generativeai as genai

        source, confidence = self._classify(question)

        # Combine main system prompt with student context for this run
        system_instruction = self.system_prompt
        if student_context:
            system_instruction += (
                "\n\n--- BEGIN STUDENT PROFILE ---\n"
                f"{student_context}\n"
                "--- END STUDENT PROFILE ---\n"
                "Use the above student profile data to answer any personalised "
                "questions about the student's GPA, remaining credit hours, "
                "completed courses, enrolled courses, etc. "
                "NEVER reveal or mention the student's password."
            )

        # Instantiate Gemini model with dynamic system instruction
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            system_instruction=system_instruction
        )

        # Build contents array
        contents = []

        # Add history
        if history:
            recent = history[-MAX_HISTORY_MESSAGES:]
            for msg in recent:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ("user", "assistant") and content:
                    role_name = "user" if role == "user" else "model"
                    contents.append({
                        "role": role_name,
                        "parts": [content]
                    })

        # Add the current question
        contents.append({
            "role": "user",
            "parts": [question]
        })

        try:
            response = model.generate_content(
                contents,
                generation_config=genai.types.GenerationConfig(
                    temperature=GEMINI_TEMPERATURE,
                    max_output_tokens=GEMINI_MAX_TOKENS,
                )
            )
            answer = response.text.strip()
        except Exception as exc:
            logger.error("Failed to generate content via Gemini: %s", exc)
            answer = "I couldn't generate an answer for that question. Please try rephrasing it."

        return {
            "answer": answer,
            "source": source,
            "confidence": confidence,
        }


# ── Singleton ─────────────────────────────────────────────────────────────────
_advisor_instance: Optional[AdvisorChain] = None


def _is_valid_key(key: str | None) -> bool:
    return bool(key and "CHANGE_ME" not in key and len(key.strip()) > 10)


def get_advisor() -> Optional[AdvisorChain]:
    """Return a Gemini advisor, building it on first call.

    Only successful instances are cached. If init fails (missing key,
    network blip, SDK error) we return None and try again on the next
    call, so a transient failure cannot lock the worker into demo mode.
    """
    global _advisor_instance
    if _advisor_instance is not None:
        return _advisor_instance

    load_dotenv(BASE_DIR / ".env")

    gemini_key = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GROQ_API_KEY", "").strip()

    if not _is_valid_key(gemini_key):
        logger.warning("GEMINI_API_KEY not set — running demo mode.")
        return None

    try:
        _advisor_instance = GeminiAdvisorChain(gemini_key)
        return _advisor_instance
    except Exception as exc:
        logger.error("Failed to initialise GeminiAdvisorChain: %s", exc)
        return None
