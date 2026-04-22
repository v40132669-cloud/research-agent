from __future__ import annotations

import json
import logging
import os
from typing import AsyncGenerator, ClassVar

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator

from graph import build_graph

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(override=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

os.makedirs("static", exist_ok=True)

app = FastAPI(title="自动化研报 Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


class ResearchRequest(BaseModel):
    MAX_TOPIC_LENGTH: ClassVar[int] = 200
    topic: str

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("主题不能为空")
        topic = value.strip()
        if len(topic) > cls.MAX_TOPIC_LENGTH:
            raise ValueError(f"主题长度不能超过 {cls.MAX_TOPIC_LENGTH} 个字符")
        return topic


class ResearchResponse(BaseModel):
    status: str
    message: str


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    with open("templates/index.html", "r", encoding="utf-8") as file:
        html_content = file.read()
    return HTMLResponse(content=html_content)


@app.post("/api/research")
async def start_research(request: ResearchRequest) -> ResearchResponse:
    topic = request.topic
    try:
        result = await run_research(topic)
        return ResearchResponse(status="success", message=result)
    except ValueError as exc:
        logger.warning("Research validation error: %s", exc)
        return ResearchResponse(status="error", message=str(exc))
    except Exception:
        logger.exception("Research failed")
        return ResearchResponse(status="error", message="调研失败，请稍后重试")


@app.api_route("/api/research/stream", methods=["GET", "POST"])
async def stream_research(request: Request):
    if request.method == "GET":
        return {"message": "Use POST to start research"}

    body = await request.body()
    data = json.loads(body) if body else {}
    topic = data.get("topic", "") or "default"

    return StreamingResponse(
        research_stream_generator(topic),
        media_type="text/event-stream",
    )


async def research_stream_generator(topic: str) -> AsyncGenerator[str, None]:
    try:
        async with build_graph() as app_graph:
            config = {"configurable": {"thread_id": f"research::{topic}"}}
            initial_state = {
                "topic": topic,
                "plan": [],
                "queries": [],
                "content": [],
                "analysis": {},
                "analysis_summary": "",
                "review": {},
                "report": "",
                "revision_count": 0,
            }

            yield f'data: {json.dumps({"type": "start", "topic": topic}, ensure_ascii=False)}\n\n'

            async for event in app_graph.astream(
                initial_state, config=config, stream_mode="updates"
            ):
                node_name = list(event.keys())[0] if event else "unknown"
                node_data = event.get(node_name, {})

                if node_name == "planner":
                    payload = {"type": "plan", "data": node_data.get("plan", [])}
                elif node_name == "researcher":
                    payload = {
                        "type": "research",
                        "content_count": len(node_data.get("content", [])),
                    }
                elif node_name == "analyst":
                    payload = {
                        "type": "analysis",
                        "summary": node_data.get("analysis_summary", ""),
                    }
                elif node_name == "reviewer":
                    review = node_data.get("review", {})
                    payload = {"type": "review", "decision": review.get("decision")}
                elif node_name == "writer":
                    payload = {"type": "report", "report": node_data.get("report", "")}
                else:
                    payload = {"type": "progress", "node": node_name}

                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

            final_state = await app_graph.aget_state(config)
            values = final_state.values
            payload = {
                "type": "complete",
                "report": values.get("report", ""),
                "analysis": values.get("analysis", {}),
            }
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    except ValueError as exc:
        logger.warning("Stream research validation error: %s", exc)
        yield f'data: {json.dumps({"type": "error", "message": str(exc)}, ensure_ascii=False)}\n\n'
    except Exception:
        logger.exception("Stream research failed")
        yield f'data: {json.dumps({"type": "error", "message": "调研失败，请稍后重试"}, ensure_ascii=False)}\n\n'


async def run_research(topic: str) -> str:
    async with build_graph() as app_graph:
        config = {"configurable": {"thread_id": f"research::{topic}"}}
        initial_state = {
            "topic": topic,
            "plan": [],
            "queries": [],
            "content": [],
            "analysis": {},
            "analysis_summary": "",
            "review": {},
            "report": "",
            "revision_count": 0,
        }

        async for _ in app_graph.astream(initial_state, config=config, stream_mode="updates"):
            pass

        final_state = await app_graph.aget_state(config)
        return final_state.values.get("report", "")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "7000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
