from pydantic import BaseModel

from app.services.llm_service import LLMService


class ExpandedQueries(BaseModel):
    queries: list[str]


SYSTEM_PROMPT = (
    "You are a query expansion assistant for a portfolio search system. "
    "Given a user query about a person's portfolio (skills, projects, experience, education), "
    "generate exactly 2 alternative phrasings that capture different aspects or wordings "
    "of the same intent. Keep queries concise and focused."
)


class QueryExpander:
    """Generates variant phrasings of a query using LLM structured output."""

    def __init__(self, llm: LLMService) -> None:
        self.llm = llm

    def expand(self, query: str) -> list[str]:
        """Return 3 variant phrasings of the original query."""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Generate 2 variant phrasings for: {query}"},
        ]
        result = self.llm.chat_structured(messages, ExpandedQueries)
        return result.queries[:2]
