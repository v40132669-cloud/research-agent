from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
from datetime import datetime
from typing import Any
from urllib.parse import urlencode, urlparse

import websockets
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from state import AgentState
from tools import create_search_tool

logger = logging.getLogger(__name__)

MAX_LOOPS = 2
MAX_DOC_LEN = 2000
MAX_DOCS_MAP = 10
MAX_LLM_RETRIES = 4
MAP_CONCURRENCY = 2


def get_qwen_llm() -> ChatOpenAI:
    """Return a Qwen-compatible OpenAI client."""
    api_key = os.getenv("DASHSCOPE_API_KEY")
    base_url = os.getenv(
        "DASHSCOPE_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    model = os.getenv("QWEN_MODEL", "qwen3-max")
    temperature = float(os.getenv("MODEL_TEMPERATURE", "0.2"))

    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
    )


def get_xunfei_llm() -> "XunfeiSparkLLM":
    """Return a Xunfei Spark client backed by native WebSocket calls."""
    compound_key = os.getenv("XUNFEI_API_KEY", "")
    api_key, api_secret = "", ""
    if ":" in compound_key:
        api_key, api_secret = compound_key.split(":", 1)

    return XunfeiSparkLLM(
        app_id=os.getenv("XUNFEI_APP_ID", ""),
        api_key=api_key,
        api_secret=api_secret,
        domain=os.getenv("XUNFEI_MODEL", "general"),
        temperature=float(os.getenv("MODEL_TEMPERATURE", "0.2")),
        url=os.getenv("XUNFEI_BASE_URL", "wss://spark-api.xf-yun.com/v1.1/chat"),
    )


class XunfeiSparkLLM:
    """Minimal wrapper for Xunfei Spark chat over WebSocket."""

    def __init__(
        self,
        app_id: str,
        api_key: str,
        api_secret: str,
        domain: str = "general",
        temperature: float = 0.2,
        url: str = "wss://spark-api.xf-yun.com/v1.1/chat",
    ) -> None:
        self.app_id = app_id
        self.api_key = api_key
        self.api_secret = api_secret
        self.domain = domain
        self.temperature = temperature
        self.url = url

    def _create_url(self) -> str:
        parsed = urlparse(self.url)
        host = parsed.netloc
        path = parsed.path
        date = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
        signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"

        signature_sha = hmac.new(
            self.api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature_sha_base64 = base64.b64encode(signature_sha).decode("utf-8")

        authorization_origin = (
            f'api_key="{self.api_key}", algorithm="hmac-sha256", '
            f'headers="host date request-line", signature="{signature_sha_base64}"'
        )
        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode(
            "utf-8"
        )
        params = {"host": host, "date": date, "authorization": authorization}
        return self.url + "?" + urlencode(params)

    def _build_request(self, prompt: str) -> dict[str, Any]:
        return {
            "header": {"app_id": self.app_id, "uid": "user_001"},
            "parameter": {
                "chat": {
                    "domain": self.domain,
                    "temperature": self.temperature,
                    "max_tokens": 2048,
                }
            },
            "payload": {
                "message": {"text": [{"role": "user", "content": prompt}]}
            },
        }

    async def _achat(self, prompt: str) -> str:
        url = self._create_url()

        async with websockets.connect(url) as ws:
            await ws.send(json.dumps(self._build_request(prompt)))

            response_text = ""
            while True:
                response = await ws.recv()
                data = json.loads(response)
                status = data.get("header", {}).get("status", 2)
                content = (
                    data.get("payload", {})
                    .get("choices", {})
                    .get("message", {})
                    .get("content", "")
                )
                if content:
                    response_text += content
                if status == 2:
                    break

            return response_text

    def invoke(self, prompt: str) -> AIMessage:
        result = asyncio.run(self._achat(prompt))
        return AIMessage(content=result)

    async def ainvoke(self, prompt: str) -> AIMessage:
        result = await self._achat(prompt)
        return AIMessage(content=result)


def get_llm():
    provider = os.getenv("MODEL_PROVIDER", "openai").lower()
    temperature = float(os.getenv("MODEL_TEMPERATURE", "0.2"))

    if provider == "anthropic":
        return ChatAnthropic(
            model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
            temperature=temperature,
        )
    if provider == "qwen":
        return get_qwen_llm()
    if provider == "xunfei":
        return get_xunfei_llm()

    base_url = os.getenv("OPENAI_BASE_URL")
    kwargs: dict[str, Any] = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o"),
        "temperature": temperature,
    }
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)


def _json_text(value: Any) -> str:
    content = value.content if hasattr(value, "content") else value
    return content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)


def _extract_json_block(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"Model did not return JSON: {text}")
    return text[start : end + 1]


def _compact_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def _truncate_doc(doc: dict[str, Any]) -> dict[str, Any]:
    """Trim overly long documents to reduce token usage."""
    cloned = dict(doc)
    text = json.dumps(cloned, ensure_ascii=False)
    if len(text) > MAX_DOC_LEN:
        cloned["body"] = cloned.get("body", "")[:MAX_DOC_LEN]
        cloned["raw_content"] = cloned.get("raw_content", "")[:MAX_DOC_LEN]
    return cloned


def _dedupe_queries(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item.strip() for item in items if item and item.strip()))


def _is_retryable_llm_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        "请求限频" in str(exc)
        or "rate" in message
        or "429" in message
        or "2003" in message
        or "timeout" in message
    )


async def _ainvoke_llm(llm: Any, messages: list[Any]) -> Any:
    delay = 2.0
    for attempt in range(1, MAX_LLM_RETRIES + 1):
        try:
            return await llm.ainvoke(messages)
        except Exception as exc:
            if attempt == MAX_LLM_RETRIES or not _is_retryable_llm_error(exc):
                raise
            logger.warning(
                "LLM call failed on attempt %s/%s: %s; retrying in %.1fs",
                attempt,
                MAX_LLM_RETRIES,
                exc,
                delay,
            )
            await asyncio.sleep(delay)
            delay *= 2


async def planner_node(state: AgentState) -> dict[str, Any]:
    llm = get_llm()
    topic = state["topic"]
    revision_count = state.get("revision_count", 0)
    review = state.get("review", {})
    logger.info("Planner started for topic=%s revision=%s", topic, revision_count)

    prompt = """
你是一名专业投研分析师。请将用户的调研主题拆解为可执行的搜索计划。

只输出 JSON，格式如下：
{
  "plan": [
    {"dimension": "", "objective": "", "query": ""}
  ],
  "queries": []
}

要求：
1. 生成 3-5 个维度。
2. 每个维度必须包含 dimension、objective、query。
3. query 必须具体、可检索、适合互联网搜索。
4. 如果上一轮审核指出缺口，优先补齐缺口。
"""

    response = await _ainvoke_llm(
        llm,
        [
            SystemMessage(content=prompt),
            HumanMessage(
                content=(
                    f"调研主题：{topic}\n"
                    f"当前修正轮次：{revision_count}\n"
                    f"上一轮审核反馈：{_compact_json(review) if review else '无'}"
                )
            ),
        ]
    )
    payload = json.loads(_extract_json_block(_json_text(response)))
    plan = payload.get("plan", [])[:5]
    queries = _dedupe_queries(payload.get("queries", [])[:5])
    logger.info("Planner generated %s dimensions and %s queries", len(plan), len(queries))
    return {"plan": plan, "queries": queries}


async def researcher_node(state: AgentState) -> dict[str, Any]:
    tool = create_search_tool(
        max_results=int(os.getenv("TAVILY_MAX_RESULTS", "8")),
        top_k_per_query=int(os.getenv("TAVILY_TOP_K", "5")),
    )
    topic = state["topic"]
    plan = state.get("plan", [])
    logger.info("Researcher started with %s plan items", len(plan))

    tasks = [
        tool.search(item.get("query", ""), topic, dimension=item.get("dimension"))
        for item in plan
        if item.get("query")
    ]
    search_results = await asyncio.gather(*tasks)

    content: list[dict[str, Any]] = []
    for result in search_results:
        content.extend(result["results"])

    logger.info("Researcher collected %s filtered documents", len(content))
    return {
        "content": content,
        "revision_count": state.get("revision_count", 0) + 1,
    }


async def _map_single_document(
    llm: Any, topic: str, document: dict[str, Any]
) -> dict[str, Any]:
    prompt = """
你是一名研究助理，请对单篇材料进行去噪抽取。

只输出 JSON，格式如下：
{
  "dimension": "",
  "source_url": "",
  "title": "",
  "facts": [
    {"claim": "", "numbers": [], "dates": [], "evidence": ""}
  ]
}

要求：
1. 剔除广告、公关稿和空泛表述。
2. 尽量保留数字、日期、价格、用户量、财务指标等客观信息。
3. 所有结论都要可追溯到来源。
"""

    response = await _ainvoke_llm(
        llm,
        [
            SystemMessage(content=prompt),
            HumanMessage(
                content=(
                    f"调研主题：{topic}\n"
                    f"材料：{_compact_json(_truncate_doc(document))}"
                )
            ),
        ]
    )
    return json.loads(_extract_json_block(_json_text(response)))


async def analyst_node(state: AgentState) -> dict[str, Any]:
    llm = get_llm()
    documents = state.get("content", [])[:MAX_DOCS_MAP]
    logger.info("Analyst started with %s raw items", len(documents))

    semaphore = asyncio.Semaphore(MAP_CONCURRENCY)

    async def _run_map(document: dict[str, Any]) -> dict[str, Any]:
        async with semaphore:
            return await _map_single_document(llm, state["topic"], document)

    map_results = await asyncio.gather(*[_run_map(document) for document in documents])

    reduce_prompt = """
你是一名卖方研究分析师，需要将多篇材料的抽取结果汇总成结构化分析。

只输出 JSON，格式如下：
{
  "summary": "整体判断",
  "facts": [
    {
      "dimension": "",
      "claim": "",
      "numbers": [],
      "dates": [],
      "source_url": "",
      "supporting_sources": []
    }
  ],
  "gaps": [],
  "source_count": 0
}

要求：
1. 只保留客观、可验证的信息。
2. 合并重复事实，尽量体现交叉验证。
3. 明确写出仍然缺失的信息。
"""

    response = await _ainvoke_llm(
        llm,
        [
            SystemMessage(content=reduce_prompt),
            HumanMessage(
                content=(
                    f"调研主题：{state['topic']}\n"
                    f"规划维度：{_compact_json(state.get('plan', []))}\n"
                    f"Map 结果：{_compact_json(map_results)}"
                )
            ),
        ]
    )
    analysis = json.loads(_extract_json_block(_json_text(response)))
    analysis_summary = analysis.get("summary", "")
    logger.info("Analyst extracted %s facts", len(analysis.get("facts", [])))
    return {"analysis": analysis, "analysis_summary": analysis_summary}


async def reviewer_node(state: AgentState) -> dict[str, Any]:
    llm = get_llm()
    logger.info("Reviewer started")

    prompt = """
你是一名严苛的研究总监，请审核当前分析结果是否足以进入写作阶段。

只输出 JSON，格式如下：
{
  "decision": "approve" 或 "retry",
  "reason": "",
  "missing_items": [],
  "missing_dimensions": [],
  "confidence": 0.0
}

审核重点：
1. 是否覆盖规划维度。
2. 是否包含数字、日期和来源链接。
3. 是否存在关键缺口或缺乏交叉验证。
"""

    response = await _ainvoke_llm(
        llm,
        [
            SystemMessage(content=prompt),
            HumanMessage(
                content=(
                    f"调研主题：{state['topic']}\n"
                    f"当前修正轮次：{state.get('revision_count', 0)} / {MAX_LOOPS}\n"
                    f"规划维度：{_compact_json(state.get('plan', []))}\n"
                    f"结构化分析：{_compact_json(state.get('analysis', {}))}"
                )
            ),
        ]
    )
    review = json.loads(_extract_json_block(_json_text(response)))
    logger.info("Reviewer decision=%s", review.get("decision"))
    return {"review": review}


def reviewer_router(state: AgentState) -> str:
    review = state.get("review", {})
    decision = review.get("decision", "retry")
    revision_count = state.get("revision_count", 0)

    if decision == "approve" or revision_count >= MAX_LOOPS:
        return "writer"
    return "planner"


async def writer_node(state: AgentState) -> dict[str, Any]:
    llm = get_llm()
    logger.info("Writer started")

    prompt = """
你是一名投行风格分析师，请基于已有事实撰写 Markdown 研报。

报告结构必须包含：
1. 背景
2. 核心竞争力
3. SWOT
4. 风险
5. 结论
6. 参考来源

要求：
1. 结论先行。
2. 尽量引用数字、日期和来源。
3. 对证据不足处保持谨慎措辞。
"""

    response = await _ainvoke_llm(
        llm,
        [
            SystemMessage(content=prompt),
            HumanMessage(
                content=(
                    f"调研主题：{state['topic']}\n"
                    f"规划维度：{_compact_json(state.get('plan', []))}\n"
                    f"分析摘要：{state.get('analysis_summary', '')}\n"
                    f"结构化分析：{_compact_json(state.get('analysis', {}))}\n"
                    f"审核意见：{_compact_json(state.get('review', {}))}"
                )
            ),
        ]
    )
    return {"report": _json_text(response)}
