import os
import logging
from typing import Optional
from dotenv import load_dotenv
from pathlib import Path

logger = logging.getLogger(__name__)

# تأكيد قراءة ملف .env القادم من المجلد الرئيسي للباك إند
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

SIMILARITY_THRESHOLD = 0.7
TOP_K = 3

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
    "The student's question is not covered by the official university records, "
    "so answer as a helpful general AI assistant with expertise in computer science, "
    "academic guidance, and career development. Keep answers practical and encouraging."
)

GENERAL_PROMPT = """{system}

Student Question: {question}

Answer (general AI knowledge — not from official records):"""


class HybridAdvisorChain:
    def __init__(self) -> None:
        from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
        from pinecone._client import Pinecone

        gemini_key = os.getenv("GEMINI_API_KEY", "")
        pinecone_key = os.getenv("PINECONE_API_KEY", "")
        index_name = os.getenv("PINECONE_INDEX_NAME", "just-cs-advisor")

        if not gemini_key or not pinecone_key:
            raise RuntimeError("Missing API Keys inside Environment Variables.")

        # تهيئة جيميناي 2.0 فلاش للردود السريعة
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=gemini_key,
            temperature=0.3,
        )

        # نماذج التضمين والمطابقة مع فيكتور باينكون
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=gemini_key,
            task_type="retrieval_query",
            output_dimensionality=768,
        )

        pc = Pinecone(api_key=pinecone_key)
        self.index = pc.Index(index_name)
        logger.info("HybridAdvisorChain initialised successfully (index=%s)", index_name)

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


_advisor_instance: Optional[HybridAdvisorChain] = None
_init_attempted: bool = False


def get_advisor() -> Optional[HybridAdvisorChain]:
    global _advisor_instance, _init_attempted
    if _init_attempted:
        return _advisor_instance
    _init_attempted = True

    # جلب المفاتيح بشكل مباشر مع الحماية الآمنة للداتا بيز
    gemini_key = os.getenv("GEMINI_API_KEY")
    pinecone_key = os.getenv("PINECONE_API_KEY")

    if not gemini_key or not pinecone_key or "CHANGE_ME" in gemini_key:
        logger.warning("GEMINI_API_KEY or PINECONE_API_KEY not set properly — Running Demo Mode.")
        return None

    try:
        _advisor_instance = HybridAdvisorChain()
    except Exception as exc:
        logger.error("Failed to initialise HybridAdvisorChain: %s", exc)
        _advisor_instance = None

    return _advisor_instance