import os
import logging
from typing import Optional, Protocol
from dotenv import load_dotenv
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

SIMILARITY_THRESHOLD = 0.7
TOP_K = 3

JUST_ADVISOR_SYSTEM = (
    "You are the official AI Academic Advisor for the Computer Science department "
    "at Jordan University of Science and Technology (JUST). "
    "Help students with course prerequisites, graduation requirements (132 credit hours), "
    "GPA calculation, practical training (CS391), graduation projects (CS491/CS492), "
    "and general CS academic guidance. "
    "Be specific, cite course codes when relevant, and keep answers professional yet friendly. "
    "If you are unsure about a JUST-specific policy, say so and suggest contacting the department."
)

OFFICIAL_SYSTEM = (
    "You are the official Academic Advisor for the Computer Science department "
    "at Jordan University of Science and Technology (JUST). "
    "Answer the student's question using ONLY the official university information "
    "provided below. Be specific, cite course codes or regulation sections where "
    "relevant, and keep the tone professional yet friendly."
)

OFFICIAL_PROMPT = """{system}

--- Official JUST CS Department Data ---
{context}
-----------------------------------------

Student Question: {question}

Answer based strictly on the above official data:"""

GENERAL_SYSTEM = (
    "You are a knowledgeable AI Academic Advisor for Computer Science students at "
    "Jordan University of Science and Technology (JUST). "
    "Answer helpfully with expertise in computer science, academic guidance, and career development. "
    "Keep answers practical and encouraging."
)

GENERAL_PROMPT = """{system}

Student Question: {question}

Answer:"""


class AdvisorChain(Protocol):
    def query(self, question: str) -> dict: ...


class GeminiAdvisorChain:
    """Direct Gemini chat — used when Pinecone RAG is unavailable."""

    def __init__(self, gemini_key: str) -> None:
        from langchain_google_genai import ChatGoogleGenerativeAI

        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=gemini_key,
            temperature=0.3,
        )
        logger.info("GeminiAdvisorChain initialised (direct Gemini mode)")

    def query(self, question: str) -> dict:
        from langchain_core.messages import HumanMessage, SystemMessage

        response = self.llm.invoke([
            SystemMessage(content=JUST_ADVISOR_SYSTEM),
            HumanMessage(content=question),
        ])

        return {
            "answer": response.content,
            "source": "general",
            "confidence": 0.0,
        }


class HybridAdvisorChain:
    """Pinecone RAG + Gemini — official data when similarity is high."""

    def __init__(self, gemini_key: str, pinecone_key: str, index_name: str) -> None:
        from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
        from pinecone import Pinecone

        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=gemini_key,
            temperature=0.3,
        )

        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=gemini_key,
            task_type="retrieval_query",
            output_dimensionality=768,
        )

        pc = Pinecone(api_key=pinecone_key)
        self.index = pc.Index(index_name)
        logger.info("HybridAdvisorChain initialised (RAG mode, index=%s)", index_name)

    def query(self, question: str) -> dict:
        query_vector = self.embeddings.embed_query(question)
        results = self.index.query(vector=query_vector, top_k=TOP_K, include_metadata=True)

        top_score: float = results.matches[0].score if results.matches else 0.0

        if top_score >= SIMILARITY_THRESHOLD:
            chunks = [m.metadata.get("text", "") for m in results.matches if m.score >= SIMILARITY_THRESHOLD]
            context = "\n\n".join(chunks)
            prompt_text = OFFICIAL_PROMPT.format(system=OFFICIAL_SYSTEM, context=context, question=question)
            source = "official"
        else:
            prompt_text = GENERAL_PROMPT.format(system=GENERAL_SYSTEM, question=question)
            source = "general"

        from langchain_core.messages import HumanMessage
        response = self.llm.invoke([HumanMessage(content=prompt_text)])

        return {
            "answer": response.content,
            "source": source,
            "confidence": round(float(top_score), 3),
        }


_advisor_instance: Optional[AdvisorChain] = None
_init_attempted: bool = False


def _is_valid_key(key: str | None) -> bool:
    return bool(key and "CHANGE_ME" not in key and len(key.strip()) > 10)


def get_advisor() -> Optional[AdvisorChain]:
    global _advisor_instance, _init_attempted
    if _init_attempted:
        return _advisor_instance
    _init_attempted = True

    load_dotenv(BASE_DIR / ".env")

    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    pinecone_key = os.getenv("PINECONE_API_KEY", "").strip()
    index_name = os.getenv("PINECONE_INDEX_NAME", "just-cs-advisor")

    if not _is_valid_key(gemini_key):
        logger.warning("GEMINI_API_KEY not set — running demo mode.")
        return None

    if _is_valid_key(pinecone_key):
        try:
            _advisor_instance = HybridAdvisorChain(gemini_key, pinecone_key, index_name)
            return _advisor_instance
        except Exception as exc:
            logger.warning("Hybrid RAG init failed (%s) — falling back to direct Gemini.", exc)

    try:
        _advisor_instance = GeminiAdvisorChain(gemini_key)
    except Exception as exc:
        logger.error("Failed to initialise GeminiAdvisorChain: %s", exc)
        _advisor_instance = None

    return _advisor_instance
