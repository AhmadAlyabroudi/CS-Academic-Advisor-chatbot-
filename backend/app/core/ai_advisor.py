"""
Hybrid AI Academic Advisor — LangChain Orchestration Layer

Pipeline (matches the flowchart in Ai integration tool flowchart.png):
  1. Embed student query  →  Google gemini-embedding-001
  2. Semantic search       →  Pinecone vector index (JUST CS knowledge base)
  3. Threshold gate        →  score ≥ 0.7 → Official Mode, else → General Mode
  4. Prompt construction   →  Official: grounded in retrieved university chunks
                              General:  free-form AI assistant fallback
  5. LLM generation        →  Gemini 2.0 Flash (via LangChain)
  6. Tagged response       →  source = "official" | "general"
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

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
    """
    LangChain-orchestrated hybrid RAG chain.
    Initialisation is deferred until first use; the module-level
    `get_advisor()` factory handles lazy construction.
    """

    def __init__(self) -> None:
        from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
        from pinecone._client import Pinecone  # v9 lazy-exports via __init__.__getattr__
        from langchain_core.messages import HumanMessage

        gemini_key = os.getenv("GEMINI_API_KEY", "AIzaSyA6xqRb1IwbCSfIRAwiRaKhxHFtpe0A0Wc")
        pinecone_key = os.getenv("PINECONE_API_KEY", "pcsk_5ZhAg2_PzMVddVpLTJaRTvVkXCfa3Q8rafiUi6Lr4zHRwwrSuz3S191zBVKwJZDWuoLtkw")
        index_name = os.getenv("PINECONE_INDEX_NAME", "just-cs-advisor")

        if not gemini_key:
            raise RuntimeError("GEMINI_API_KEY environment variable is not set.")
        if not pinecone_key:
            raise RuntimeError("PINECONE_API_KEY environment variable is not set.")

        # ── LangChain LLM (Gemini 2.0 Flash) ────────────────────────────────────
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=gemini_key,
            temperature=0.3,
        )

        # ── Embedding model (Google gemini-embedding-001, 768-dim truncated) ───
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=gemini_key,
            task_type="retrieval_query",
            output_dimensionality=768,  # match Pinecone index dimension
        )

        # ── Pinecone index ───────────────────────────────────────────────────────
        pc = Pinecone(api_key=pinecone_key)
        self.index = pc.Index(index_name)

        logger.info("HybridAdvisorChain initialised (index=%s)", index_name)

    # ── Public API ───────────────────────────────────────────────────────────────

    def query(self, question: str) -> dict:
        """
        Execute the hybrid RAG pipeline for one student question.

        Returns:
            {
                "answer":     str,
                "source":     "official" | "general",
                "confidence": float,   # top Pinecone similarity score
            }
        """
        # Phase 1 — embed the query
        query_vector = self.embeddings.embed_query(question)

        # Phase 2 — semantic search in Pinecone
        results = self.index.query(
            vector=query_vector,
            top_k=TOP_K,
            include_metadata=True,
        )

        top_score: float = results.matches[0].score if results.matches else 0.0

        # Phase 3 — threshold decision
        if top_score >= SIMILARITY_THRESHOLD:
            # Official mode: extract relevant chunks above threshold
            chunks = [
                m.metadata.get("text", "")
                for m in results.matches
                if m.score >= SIMILARITY_THRESHOLD
            ]
            context = "\n\n".join(chunks)
            prompt_text = OFFICIAL_PROMPT.format(
                system=OFFICIAL_SYSTEM,
                context=context,
                question=question,
            )
            source = "official"
        else:
            # General fallback mode
            prompt_text = GENERAL_PROMPT.format(
                system=GENERAL_SYSTEM,
                question=question,
            )
            source = "general"

        # Phase 4 — LLM generation via LangChain
        from langchain_core.messages import HumanMessage
        response = self.llm.invoke([HumanMessage(content=prompt_text)])

        return {
            "answer": response.content,
            "source": source,
            "confidence": round(float(top_score), 3),
        }


# ── Module-level lazy singleton ──────────────────────────────────────────────

_advisor_instance: Optional[HybridAdvisorChain] = None
_init_attempted: bool = False


def get_advisor() -> Optional[HybridAdvisorChain]:
    """
    Return the singleton HybridAdvisorChain, or None if API keys are absent.
    Logs a warning (not an error) when keys are missing so the app starts
    normally and degrades gracefully.
    """
    global _advisor_instance, _init_attempted
    if _init_attempted:
        return _advisor_instance
    _init_attempted = True

    if not os.getenv("GEMINI_API_KEY") or not os.getenv("PINECONE_API_KEY"):
        logger.warning(
            "GEMINI_API_KEY or PINECONE_API_KEY not set — "
            "AI chatbot will operate in demo mode."
        )
        return None

    try:
        _advisor_instance = HybridAdvisorChain()
    except Exception as exc:
        logger.error("Failed to initialise HybridAdvisorChain: %s", exc)
        _advisor_instance = None

    return _advisor_instance
