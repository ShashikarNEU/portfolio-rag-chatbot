from pydantic import BaseModel, Field
from uuid import uuid4


class ChatRequest(BaseModel):
    message: str
    thread_id: str = Field(default_factory=lambda: str(uuid4()))


class Source(BaseModel):
    document: str
    chunk: str
    relevance_score: float


class ChatResponse(BaseModel):
    response: str
    thread_id: str
    sources: list[Source] = []
    email_sent: bool = False
