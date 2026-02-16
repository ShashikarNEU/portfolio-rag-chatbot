import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.config import settings
from app.graph.tools import tools
from app.graph.worker import Worker
from app.models.state import State


def build_graph(db_path: str | None = None) -> StateGraph:
    """Build and compile the LangGraph with worker + tools nodes."""
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

    checkpointer = SqliteSaver(
        sqlite3.connect(db_path, check_same_thread=False)
    )
    return workflow.compile(checkpointer=checkpointer)
