from typing import TypeVar

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pydantic import BaseModel

from app.config import settings

T = TypeVar("T", bound=BaseModel)


class LLMService:
    """LangChain wrapper for chat completions and embeddings."""

    def __init__(self) -> None:
        self.llm = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
            temperature=0,
        )
        self.embeddings = OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
        )

    def chat(self, messages: list[dict]) -> str:
        """Send messages and return the text response."""
        response = self.llm.invoke(messages)
        return response.content

    def chat_structured(
        self,
        messages: list[dict],
        response_format: type[T],
    ) -> T:
        """Send messages and parse the response into a Pydantic model."""
        structured_llm = self.llm.with_structured_output(response_format)
        return structured_llm.invoke(messages)

    def embed(self, text: str) -> list[float]:
        """Embed a single text string."""
        return self.embeddings.embed_query(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts in a single call."""
        return self.embeddings.embed_documents(texts)
