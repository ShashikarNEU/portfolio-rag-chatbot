from pathlib import Path

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.config import settings
from app.graph.tools import tools
from app.graph.worker import Worker
from app.models.state import State


async def build_graph(
    db_path: str | None = None,
) -> tuple[StateGraph, AsyncSqliteSaver, aiosqlite.Connection]:
    """Build and compile the LangGraph with async checkpointer.

    Returns (compiled_graph, checkpointer, aiosqlite_connection) so the
    caller can store the checkpointer and close the connection on shutdown.
    """
    if db_path is None:
        db_path = settings.sqlite_db_path

    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    worker = Worker()
    tool_node = ToolNode(tools)

    workflow = StateGraph(State)
    workflow.add_node("worker", worker)
    workflow.add_node("tools", tool_node)

    workflow.add_edge(START, "worker")
    workflow.add_conditional_edges(
        "worker", tools_condition, {"tools": "tools", END: END}
    )
    workflow.add_edge("tools", "worker")

    conn = await aiosqlite.connect(db_path)
    checkpointer = AsyncSqliteSaver(conn)
    await checkpointer.setup()

    return workflow.compile(checkpointer=checkpointer), checkpointer, conn
