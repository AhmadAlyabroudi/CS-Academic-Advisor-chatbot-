import os
import re
import logging
from typing import Optional, Protocol
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"
load_dotenv(BASE_DIR / ".env")

GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_TEMPERATURE = 0.3
GROQ_MAX_TOKENS = 1024

# Heuristic threshold: fraction of question keywords that must appear in the
# loaded knowledge base for an answer to be labelled "official".
OFFICIAL_OVERLAP_THRESHOLD = 0.30

JUST_ADVISOR_SYSTEM = (
    "You are the official AI Academic Advisor for the Computer Science department "
    "at Jordan University of Science and Technology (JUST). "
    "Help students with course prerequisites, graduation requirements (132 credit hours), "
    "GPA calculation, practical training (CS391), graduation projects (CS491/CS492), "
    "and general CS academic guidance. "
    "Be specific, cite course codes when relevant, and keep answers professional yet friendly. "
    "Prefer the official JUST CS data provided below when answering. "
    "If the official data does not cover the question, answer from general CS knowledge and "
    "tell the student to confirm JUST-specific policies with the department."
)

OFFICIAL_DATA_HEADER = "--- Official JUST CS Department Data ---"
OFFICIAL_DATA_FOOTER = "-----------------------------------------"

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
}


class AdvisorChain(Protocol):
    def query(self, question: str) -> dict: ...


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
    return {
        tok for tok in re.findall(r"[a-z0-9]+", text.lower())
        if len(tok) > 2 and tok not in _STOP_WORDS
    }


class GroqAdvisorChain:
    """Groq-backed academic advisor.

    The full knowledge base is stuffed into the system prompt (it is small
    enough to fit). For each question we compute a cheap keyword-overlap
    score against the knowledge base to decide whether the answer is more
    likely "official" or a "general" CS answer.
    """

    def __init__(self, groq_key: str) -> None:
        from groq import Groq

        self.client = Groq(api_key=groq_key)
        self.knowledge_base = _load_knowledge_base()
        self.kb_tokens = _tokenize(self.knowledge_base)

        if self.knowledge_base:
            self.system_prompt = (
                f"{JUST_ADVISOR_SYSTEM}\n\n"
                f"{OFFICIAL_DATA_HEADER}\n{self.knowledge_base}\n{OFFICIAL_DATA_FOOTER}"
            )
            logger.info(
                "GroqAdvisorChain initialised (model=%s, kb=%d chars, %d tokens)",
                GROQ_MODEL, len(self.knowledge_base), len(self.kb_tokens),
            )
        else:
            self.system_prompt = JUST_ADVISOR_SYSTEM
            logger.warning(
                "GroqAdvisorChain initialised without knowledge base — running general mode only."
            )

    def _classify(self, question: str) -> tuple[str, float]:
        if not self.kb_tokens:
            return "general", 0.0
        q_tokens = _tokenize(question)
        if not q_tokens:
            return "general", 0.0
        overlap = len(q_tokens & self.kb_tokens) / len(q_tokens)
        source = "official" if overlap >= OFFICIAL_OVERLAP_THRESHOLD else "general"
        return source, round(overlap, 3)

    def query(self, question: str) -> dict:
        source, confidence = self._classify(question)

        completion = self.client.chat.completions.create(
            model=GROQ_MODEL,
            temperature=GROQ_TEMPERATURE,
            max_tokens=GROQ_MAX_TOKENS,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": question},
            ],
        )

        answer = (completion.choices[0].message.content or "").strip()
        if not answer:
            answer = (
                "I couldn't generate an answer for that question. "
                "Please try rephrasing it."
            )

        return {
            "answer": answer,
            "source": source,
            "confidence": confidence,
        }


_advisor_instance: Optional[AdvisorChain] = None


def _is_valid_key(key: str | None) -> bool:
    return bool(key and "CHANGE_ME" not in key and len(key.strip()) > 10)


def get_advisor() -> Optional[AdvisorChain]:
    """Return a Groq advisor, building it on first call.

    Only successful instances are cached. If init fails (missing key,
    network blip, SDK error) we return None and try again on the next
    call, so a transient failure cannot lock the worker into demo mode
    for its whole lifetime.
    """
    global _advisor_instance
    if _advisor_instance is not None:
        return _advisor_instance

    load_dotenv(BASE_DIR / ".env")

    # Support both GROQ_API_KEY and the legacy GEMINI_API_KEY slot
    # (some deployments still ship the old variable name with a Groq key).
    groq_key = os.getenv("GROQ_API_KEY", "").strip() or os.getenv("GEMINI_API_KEY", "").strip()

    if not _is_valid_key(groq_key):
        logger.warning("GROQ_API_KEY not set — running demo mode.")
        return None

    try:
        _advisor_instance = GroqAdvisorChain(groq_key)
        return _advisor_instance
    except Exception as exc:
        logger.error("Failed to initialise GroqAdvisorChain: %s", exc)
        return None
