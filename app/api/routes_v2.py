from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Request
from langchain_core.messages import AIMessageChunk, HumanMessage
from sse_starlette import EventSourceResponse

from app.api.routes import _budget, limiter
from app.models.schemas import ChatRequest

router_v2 = APIRouter(tags=["chat-v2"])


def _sse_event(event: str, data: dict | str) -> dict:
    """Format an SSE event dict for EventSourceResponse."""
    return {
        "event": event,
        "data": json.dumps(data) if isinstance(data, dict) else data,
    }


@router_v2.post("/chat/stream")
@limiter.limit("10/minute")
async def chat_stream(request: Request, body: ChatRequest) -> EventSourceResponse:
    """SSE streaming endpoint using graph.astream."""

    async def event_generator() -> AsyncGenerator[dict, None]:
        # Budget check
        if not _budget.allow():
            yield _sse_event("error", {"message": "I'm resting for today. Please try again tomorrow!"})
            yield _sse_event("done", {"thread_id": body.thread_id})
            return

        corrupted = False

        try:
            graph = request.app.state.graph
            checkpointer = request.app.state.checkpointer
            config = {"configurable": {"thread_id": body.thread_id}}

            yield _sse_event("thinking", {"text": "Processing your message..."})

            sources: list[dict] = []
            email_sent: bool = False

            async for mode, chunk in graph.astream(
                {"messages": [HumanMessage(content=body.message)]},
                config=config,
                stream_mode=["messages", "updates"],
            ):
                # Disconnect detection
                if await request.is_disconnected():
                    logger.info("Client disconnected mid-stream (thread=%s)", body.thread_id)
                    break

                if mode == "messages":
                    msg_chunk, metadata = chunk
                    node = metadata.get("langgraph_node", "")

                    # Only process chunks from the worker (LLM) node
                    if node != "worker":
                        continue

                    if not isinstance(msg_chunk, AIMessageChunk):
                        continue

                    # Tool-routing chunks have tool_call_chunks
                    if msg_chunk.tool_call_chunks:
                        for tc in msg_chunk.tool_call_chunks:
                            if tc.get("name"):
                                yield _sse_event("tool_call", {
                                    "tool": tc["name"],
                                    "id": tc.get("id", ""),
                                })
                                yield _sse_event("thinking", {
                                    "text": f"Using {tc['name']}...",
                                })

                    # Content chunks are the actual response tokens
                    elif msg_chunk.content:
                        yield _sse_event("token", {"text": msg_chunk.content})

                elif mode == "updates":
                    # updates mode yields {node_name: state_delta}
                    if not isinstance(chunk, dict):
                        continue

                    # Corruption monitoring
                    if "worker" in chunk:
                        worker_state = chunk["worker"]
                        if isinstance(worker_state, dict) and worker_state.get("thread_corrupted"):
                            corrupted = True

                    if "tools" in chunk:
                        tool_state = chunk["tools"]

                        # Capture sources and email_sent from tool results
                        if "sources" in tool_state:
                            sources = tool_state["sources"]
                        if "email_sent" in tool_state:
                            email_sent = tool_state["email_sent"]

                        # Extract tool result text for the client
                        msgs = tool_state.get("messages", [])
                        for msg in msgs:
                            tool_name = getattr(msg, "name", "tool")
                            yield _sse_event("tool_result", {
                                "tool": tool_name,
                                "preview": str(msg.content)[:200],
                            })

                        yield _sse_event("thinking", {"text": "Generating response..."})

            # Final metadata events
            if sources:
                yield _sse_event("sources", {"sources": sources})

            if email_sent:
                yield _sse_event("email_status", {"sent": True})

            if corrupted:
                yield _sse_event("thread_reset", {
                    "reason": "conversation_reset",
                    "message": "Conversation was reset due to an internal issue.",
                })

            yield _sse_event("done", {"thread_id": body.thread_id})

        except Exception:
            logger.exception("SSE stream failed")
            yield _sse_event("error", {
                "message": "Sorry, something went wrong processing your message. Please try again.",
            })
            yield _sse_event("done", {"thread_id": body.thread_id})

        finally:
            # Clean up corrupted thread checkpoint so subsequent
            # requests on this thread_id don't hit BadRequestError.
            if corrupted:
                try:
                    await checkpointer.adelete_thread(body.thread_id)
                    logger.info("Deleted corrupted checkpoint (thread=%s)", body.thread_id)
                except Exception:
                    logger.exception("Failed to delete checkpoint (thread=%s)", body.thread_id)

    return EventSourceResponse(event_generator())
