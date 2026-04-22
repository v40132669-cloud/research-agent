from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class AgentState(TypedDict, total=False):
    topic: str
    plan: list[dict[str, Any]]
    queries: list[str]
    content: Annotated[list[dict[str, Any]], operator.add]
    analysis: dict[str, Any]
    analysis_summary: str
    review: dict[str, Any]
    report: str
    revision_count: int
