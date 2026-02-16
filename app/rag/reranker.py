from pydantic import BaseModel, Field

from app.config import settings
from app.services.llm_service import LLMService

SYSTEM_PROMPT = (
    "You are a relevance scoring assistant for Shashikar's portfolio. "
    "You will receive a user query and a numbered list of text chunks. "
    "Each chunk has a source file and a priority (high, medium, or low). "
    "High-priority chunks are from flagship projects and core profile files. "
    "Score EVERY chunk's relevance to the query from 0 to 10. "
    "When two chunks are similarly relevant, prefer the higher-priority chunk. "
    "Return a score and reason for every chunk, identified by its index."
)


class ChunkScore(BaseModel):
    index: int
    score: int = Field(ge=0, le=10)
    reason: str


class ChunkScoreList(BaseModel):
    scores: list[ChunkScore]


class Reranker:
    """LLM-based reranker that scores chunks for relevance and keeps top_k."""

    def __init__(self, llm: LLMService) -> None:
        self.llm = llm
        self.top_k = settings.top_k_final

    def rerank(self, query: str, chunks: list[dict]) -> list[dict]:
        """Score all chunks 0-10 for relevance in one LLM call, return top_k sorted."""
        chunk_lines = []
        for i, chunk in enumerate(chunks):
            chunk_lines.append(
                f"[{i}] (source: {chunk['source']}, priority: {chunk['priority']})\n"
                f"{chunk['text']}"
            )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Query: {query}\n\n"
                    f"Chunks:\n\n" + "\n\n".join(chunk_lines)
                ),
            },
        ]
        result = self.llm.chat_structured(messages, ChunkScoreList)

        score_map: dict[int, ChunkScore] = {s.index: s for s in result.scores}

        scored: list[dict] = []
        for i, chunk in enumerate(chunks):
            cs = score_map.get(i)
            scored.append({
                **chunk,
                "relevance_score": cs.score if cs else 0,
                "relevance_reason": cs.reason if cs else "not scored",
            })

        scored.sort(key=lambda c: c["relevance_score"], reverse=True)
        return scored[: self.top_k]
