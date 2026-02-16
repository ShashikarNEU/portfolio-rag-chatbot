"""Test the LangGraph pipeline with sample queries.

Run: uv run python scripts/test_graph.py
"""

from dotenv import load_dotenv

load_dotenv()

from uuid import uuid4  # noqa: E402

from langchain_core.messages import HumanMessage  # noqa: E402

from app.graph.builder import build_graph  # noqa: E402


def print_result(result: dict) -> None:
    """Pretty-print all messages, tool calls, and metadata."""
    for msg in result["messages"]:
        if msg.type == "human":
            continue
        elif msg.type == "ai":
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    print(f"  [Tool Call] {tc['name']}({tc['args']})")
            if msg.content:
                print(f"\nAssistant: {msg.content}")
        elif msg.type == "tool":
            preview = msg.content[:150].replace("\n", " ")
            print(f"  [Tool Result] {msg.name}: {preview}...")

    if result.get("sources"):
        print(f"\nSources ({len(result['sources'])}):")
        for s in result["sources"]:
            print(f"  - {s['document']} (relevance: {s['relevance_score']:.2f})")

    if result.get("email_sent"):
        print("\n  Email sent: True")


def test_query(
    graph: object,
    message: str,
    thread_id: str,
    description: str,
) -> None:
    """Invoke graph with a message and print results."""
    print(f"\n{'=' * 60}")
    print(f"TEST: {description}")
    print(f"User: {message}")
    print(f"Thread: {thread_id}")
    print("=" * 60)

    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(
        {"messages": [HumanMessage(content=message)]},
        config=config,
    )
    print_result(result)
    print()


def main() -> None:
    graph = build_graph("./data/test_chat_history.db")

    # Test 1: Greeting — should respond directly, no tool call
    thread1 = str(uuid4())
    test_query(graph, "Hi there", thread1, "Greeting (no tool call expected)")

    # Test 2: Portfolio question — should call search_portfolio
    thread2 = str(uuid4())
    test_query(
        graph,
        "What are Shashikar's skills?",
        thread2,
        "Portfolio question (search_portfolio expected)",
    )

    # Test 3: Contact request — should start collecting name/email/inquiry
    thread3 = str(uuid4())
    test_query(
        graph,
        "I want to contact Shashikar",
        thread3,
        "Contact request (email collection flow)",
    )

    # Test 4: Persistence — same thread as Test 2, should remember context
    test_query(
        graph,
        "Can you tell me more about his projects?",
        thread2,
        "Persistence (same thread as Test 2)",
    )


if __name__ == "__main__":
    main()
