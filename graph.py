from __future__ import annotations

import os
from contextlib import asynccontextmanager

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from nodes import (
    analyst_node,
    planner_node,
    researcher_node,
    reviewer_node,
    reviewer_router,
    writer_node,
)
from state import AgentState

try:
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
except Exception:  # pragma: no cover
    AsyncSqliteSaver = None


@asynccontextmanager
async def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("planner", planner_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("reviewer", reviewer_node)
    graph.add_node("writer", writer_node)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "researcher")
    graph.add_edge("researcher", "analyst")
    graph.add_edge("analyst", "reviewer")
    graph.add_conditional_edges(
        "reviewer",
        reviewer_router,
        {
            "planner": "planner",
            "writer": "writer",
        },
    )
    graph.add_edge("writer", END)

    debug = os.getenv("LANGGRAPH_DEBUG", "false").lower() == "true"
    sqlite_path = os.getenv("LANGGRAPH_CHECKPOINT_DB", "agent_state.db")

    if AsyncSqliteSaver is not None:
        async with AsyncSqliteSaver.from_conn_string(sqlite_path) as checkpointer:
            yield graph.compile(checkpointer=checkpointer, debug=debug)
        return

    yield graph.compile(checkpointer=MemorySaver(), debug=debug)
