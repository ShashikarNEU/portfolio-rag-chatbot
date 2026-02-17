"""Tests for the FastAPI API endpoints."""

from unittest.mock import patch

import httpx
from langchain_core.messages import AIMessage

from app.main import app


class TestHealth:
    """GET /api/v1/health"""

    async def test_health_returns_ok(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestChat:
    """POST /api/v1/chat"""

    async def test_chat_returns_response(self, client: httpx.AsyncClient) -> None:
        """Mock graph.invoke → correct ChatResponse shape returned."""
        app.state.graph.invoke.return_value = {
            "messages": [AIMessage(content="Hello! How can I help?")],
            "sources": [],
            "email_sent": False,
        }

        response = await client.post(
            "/api/v1/chat",
            json={"message": "Hi there", "thread_id": "test-thread-1"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "Hello! How can I help?"
        assert data["thread_id"] == "test-thread-1"
        assert data["sources"] == []
        assert data["email_sent"] is False

    async def test_chat_budget_exceeded(self, client: httpx.AsyncClient) -> None:
        """When daily budget is exhausted, return the resting message."""
        with patch("app.api.routes._budget") as mock_budget:
            mock_budget.allow.return_value = False
            response = await client.post(
                "/api/v1/chat",
                json={"message": "Hello", "thread_id": "test-thread-2"},
            )

        assert response.status_code == 200
        assert "resting for today" in response.json()["response"].lower()

    async def test_chat_missing_message_returns_422(
        self, client: httpx.AsyncClient,
    ) -> None:
        """Missing required 'message' field → 422 Unprocessable Entity."""
        response = await client.post(
            "/api/v1/chat",
            json={"thread_id": "test-thread-3"},
        )
        assert response.status_code == 422

    async def test_chat_graph_error_returns_friendly_message(
        self, client: httpx.AsyncClient,
    ) -> None:
        """When graph.invoke raises, the endpoint returns a friendly ChatResponse."""
        app.state.graph.invoke.side_effect = RuntimeError("Pinecone is down")

        response = await client.post(
            "/api/v1/chat",
            json={"message": "What are his skills?", "thread_id": "test-err"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "something went wrong" in data["response"].lower()
        assert data["thread_id"] == "test-err"
