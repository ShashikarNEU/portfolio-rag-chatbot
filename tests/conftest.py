"""Shared test fixtures — all tests use real APIs."""

from collections.abc import AsyncIterator

import httpx
import pytest

from app.graph.builder import build_graph
from app.main import app


@pytest.fixture(scope="session")
async def graph_and_checkpointer():
    """Build a real LangGraph with async checkpointer."""
    compiled, checkpointer, conn = await build_graph("./data/test_chat_history.db")
    yield compiled, checkpointer
    await conn.close()


@pytest.fixture(scope="session")
async def graph(graph_and_checkpointer):
    """Expose compiled graph for tests that only need the graph."""
    graph, _checkpointer = graph_and_checkpointer
    return graph


@pytest.fixture()
async def client(graph_and_checkpointer) -> AsyncIterator[httpx.AsyncClient]:
    """Async httpx test client backed by the real graph."""
    graph, checkpointer = graph_and_checkpointer
    app.state.graph = graph
    app.state.checkpointer = checkpointer
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
