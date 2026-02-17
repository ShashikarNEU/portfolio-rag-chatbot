from datetime import date

from fastapi import APIRouter, Request
from fastapi.responses import Response
from langchain_core.messages import HumanMessage
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings
from app.models.schemas import ChatRequest, ChatResponse, Source

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["chat"])


class DailyBudget:
    """In-memory daily request counter that resets at midnight."""

    def __init__(self, max_requests: int) -> None:
        self._max = max_requests
        self._count = 0
        self._date = date.today()

    def allow(self) -> bool:
        """Check budget and increment. Returns True if allowed."""
        today = date.today()
        if today != self._date:
            self._count = 0
            self._date = today
        if self._count >= self._max:
            return False
        self._count += 1
        return True


_budget = DailyBudget(settings.daily_max_requests)


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("10/minute")
def chat(request: Request, body: ChatRequest) -> ChatResponse:
    """Process a chat message through the LangGraph pipeline.

    Sync handler — FastAPI runs it in a thread pool, which is required
    because SqliteSaver does not support async operations.
    """
    if not _budget.allow():
        return ChatResponse(
            response="I'm resting for today. Please try again tomorrow!",
            thread_id=body.thread_id,
        )

    try:
        graph = request.app.state.graph
        config = {"configurable": {"thread_id": body.thread_id}}
        result = graph.invoke(
            {"messages": [HumanMessage(content=body.message)]},
            config=config,
        )

        last_message = result["messages"][-1]

        return ChatResponse(
            response=last_message.content,
            thread_id=body.thread_id,
            sources=[Source(**s) for s in result.get("sources", [])],
            email_sent=result.get("email_sent", False),
        )
    except Exception:
        return ChatResponse(
            response="Sorry, something went wrong processing your message. Please try again.",
            thread_id=body.thread_id,
        )


@router.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@router.get("/graph/image")
async def get_graph_image(request: Request) -> Response:
    """Return the LangGraph workflow as a PNG image."""
    graph = request.app.state.graph
    try:
        png_bytes = graph.get_graph().draw_mermaid_png()
        return Response(content=png_bytes, media_type="image/png")
    except Exception:
        mermaid_text = graph.get_graph().draw_mermaid()
        return Response(content=mermaid_text, media_type="text/plain")
