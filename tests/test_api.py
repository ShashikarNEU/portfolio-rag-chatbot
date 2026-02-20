"""Integration tests for the FastAPI endpoints — real LLM + real data."""

from uuid import uuid4

import httpx


class TestHealth:
    async def test_health_returns_ok(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestChat:
    async def test_greeting_response(self, client: httpx.AsyncClient) -> None:
        """Greeting should get a friendly reply, no tool calls needed."""
        tid = str(uuid4())
        response = await client.post(
            "/api/v1/chat",
            json={"message": "Hi there!", "thread_id": tid},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["response"]) > 0
        assert data["thread_id"] == tid

    async def test_skills_query_returns_response(self, client: httpx.AsyncClient) -> None:
        """Portfolio question should return a substantive answer."""
        response = await client.post(
            "/api/v1/chat",
            json={
                "message": "What are Shashikar's technical skills? Use search_portfolio.",
                "thread_id": str(uuid4()),
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["response"]) > 0

    async def test_github_query(self, client: httpx.AsyncClient) -> None:
        """GitHub question should return repo info."""
        response = await client.post(
            "/api/v1/chat",
            json={"message": "What repos does Shashikar have on GitHub?", "thread_id": str(uuid4())},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["response"]) > 0

    async def test_missing_message_returns_422(self, client: httpx.AsyncClient) -> None:
        """Missing required 'message' field → 422."""
        response = await client.post(
            "/api/v1/chat",
            json={"thread_id": str(uuid4())},
        )
        assert response.status_code == 422
