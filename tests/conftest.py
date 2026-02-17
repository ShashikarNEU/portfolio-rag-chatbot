"""Shared test fixtures.

Dummy env vars are set before any app imports so pydantic-settings
can instantiate Settings() without a real .env file.
"""

import os
from collections.abc import AsyncIterator
from unittest.mock import MagicMock

# Must be set BEFORE any app.* imports trigger Settings()
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("PINECONE_API_KEY", "test-pinecone-key")
os.environ.setdefault("SENDGRID_API_KEY", "test-sendgrid-key")
os.environ.setdefault("RECIPIENT_EMAIL", "test@example.com")

import httpx  # noqa: E402
import pytest  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture()
async def client() -> AsyncIterator[httpx.AsyncClient]:
    """Async httpx test client backed by the FastAPI ASGI app."""
    app.state.graph = MagicMock()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
