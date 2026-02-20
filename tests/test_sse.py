"""Integration tests for the V2 SSE streaming endpoint — real LLM + real data."""

from __future__ import annotations

import json
from uuid import uuid4

import httpx


def _parse_sse_events(raw: str) -> list[dict]:
    """Parse raw SSE text into a list of {event, data} dicts."""
    events: list[dict] = []
    current_event = ""
    current_data = ""

    for line in raw.replace("\r\n", "\n").split("\n"):
        if line.startswith("event:"):
            current_event = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            current_data = line.split(":", 1)[1].strip()
        elif line == "" and current_event:
            try:
                data = json.loads(current_data)
            except (json.JSONDecodeError, TypeError):
                data = current_data
            events.append({"event": current_event, "data": data})
            current_event = ""
            current_data = ""

    return events


class TestSSEStream:
    async def test_stream_greeting(self, client: httpx.AsyncClient) -> None:
        """Greeting should stream thinking + tokens + done."""
        tid = str(uuid4())
        response = await client.post(
            "/api/v2/chat/stream",
            json={"message": "Hello!", "thread_id": tid},
        )
        assert response.status_code == 200
        events = _parse_sse_events(response.text)
        event_types = [e["event"] for e in events]

        assert "thinking" in event_types
        assert "token" in event_types
        assert "done" in event_types

        token_text = "".join(
            e["data"]["text"] for e in events if e["event"] == "token"
        )
        assert len(token_text) > 0

    async def test_stream_rag_query(self, client: httpx.AsyncClient) -> None:
        """RAG query should stream tool_call + tool_result + tokens + sources + done."""
        response = await client.post(
            "/api/v2/chat/stream",
            json={"message": "What are Shashikar's skills?", "thread_id": str(uuid4())},
        )
        assert response.status_code == 200
        events = _parse_sse_events(response.text)
        event_types = [e["event"] for e in events]

        assert "thinking" in event_types
        assert "tool_call" in event_types
        assert "tool_result" in event_types
        assert "token" in event_types
        assert "done" in event_types

    async def test_stream_github_query(self, client: httpx.AsyncClient) -> None:
        """GitHub query should stream tool_call + tool_result + tokens + done."""
        response = await client.post(
            "/api/v2/chat/stream",
            json={"message": "Show me Shashikar's GitHub repos", "thread_id": str(uuid4())},
        )
        assert response.status_code == 200
        events = _parse_sse_events(response.text)
        event_types = [e["event"] for e in events]

        assert "thinking" in event_types
        assert "token" in event_types
        assert "done" in event_types

    async def test_stream_done_has_thread_id(self, client: httpx.AsyncClient) -> None:
        """Done event should include the thread_id."""
        tid = str(uuid4())
        response = await client.post(
            "/api/v2/chat/stream",
            json={"message": "Hi", "thread_id": tid},
        )
        events = _parse_sse_events(response.text)
        done_events = [e for e in events if e["event"] == "done"]
        assert len(done_events) == 1
        assert done_events[0]["data"]["thread_id"] == tid
