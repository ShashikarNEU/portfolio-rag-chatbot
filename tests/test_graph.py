"""Integration tests for the LangGraph pipeline — real LLM + tools.

Run: uv run pytest tests/test_graph.py -v
"""

from uuid import uuid4

from langchain_core.messages import HumanMessage


async def _ainvoke(graph, message: str, thread_id: str) -> dict:
    config = {"configurable": {"thread_id": thread_id}}
    return await graph.ainvoke(
        {"messages": [HumanMessage(content=message)]},
        config=config,
    )


class TestGreeting:
    async def test_greeting_no_tool_call(self, graph) -> None:
        """Greetings should respond directly without tool calls."""
        result = await _ainvoke(graph, "Hi there", str(uuid4()))
        last = result["messages"][-1]
        assert last.content
        assert not last.tool_calls


class TestPortfolioQuery:
    async def test_skills_query_uses_search(self, graph) -> None:
        """Portfolio questions should call search_portfolio and return sources."""
        result = await _ainvoke(graph, "What are Shashikar's skills?", str(uuid4()))
        last = result["messages"][-1]
        assert last.content
        assert len(result.get("sources", [])) > 0

    async def test_experience_query(self, graph) -> None:
        result = await _ainvoke(graph, "Tell me about his work experience", str(uuid4()))
        last = result["messages"][-1]
        assert last.content


class TestGitHubQuery:
    async def test_repos_query(self, graph) -> None:
        """Project questions should use GitHub tools."""
        result = await _ainvoke(graph, "What repos does Shashikar have?", str(uuid4()))
        last = result["messages"][-1]
        assert last.content


class TestContactFlow:
    async def test_contact_starts_collection(self, graph) -> None:
        """Contact request should ask for details, not send email yet."""
        result = await _ainvoke(graph, "I want to contact Shashikar", str(uuid4()))
        last = result["messages"][-1]
        assert last.content
        assert not result.get("email_sent", False)


class TestPersistence:
    async def test_same_thread_remembers_context(self, graph) -> None:
        """Same thread_id should maintain conversation context."""
        thread = str(uuid4())
        await _ainvoke(graph, "What are Shashikar's skills?", thread)
        result = await _ainvoke(graph, "Can you tell me more about his projects?", thread)
        last = result["messages"][-1]
        assert last.content
