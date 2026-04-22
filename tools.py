from __future__ import annotations

import asyncio
import logging
import os
from typing import Any
from urllib.parse import urlparse

import fitz
import httpx
from tavily import TavilyClient

logger = logging.getLogger(__name__)


class TavilySearchTool:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        search_depth: str = "advanced",
        include_raw_content: bool = True,
        max_results: int = 8,
        top_k_per_query: int = 5,
    ) -> None:
        self._api_key = api_key or os.environ.get("TAVILY_API_KEY")
        if not self._api_key:
            raise ValueError("TAVILY_API_KEY environment variable is required")
        self._client = TavilyClient(api_key=self._api_key)
        self.search_depth = search_depth
        self.include_raw_content = include_raw_content
        self.max_results = max_results
        self.top_k_per_query = top_k_per_query

    async def search(self, query: str, topic: str, dimension: str | None = None) -> dict[str, Any]:
        logger.info("Searching Tavily for query=%s", query)
        response = await asyncio.to_thread(
            self._client.search,
            query=query,
            topic="general",
            search_depth=self.search_depth,
            include_raw_content=self.include_raw_content,
            max_results=self.max_results,
        )

        ranked_results = sorted(
            response.get("results", []),
            key=lambda item: item.get("score") or 0,
            reverse=True,
        )[: self.top_k_per_query]

        results: list[dict[str, Any]] = []
        for item in ranked_results:
            entry = {
                "topic": topic,
                "dimension": dimension or "",
                "query": query,
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "score": item.get("score"),
                "published_date": item.get("published_date"),
                "snippet": item.get("content", ""),
                "raw_content": item.get("raw_content", ""),
            }
            raw_body = entry["raw_content"] or entry["snippet"]
            entry["body"] = clean_body_text(raw_body)
            if _looks_like_pdf(entry["url"]):
                entry["pdf_text"] = await fetch_pdf_text(entry["url"])
                if entry["pdf_text"]:
                    entry["body"] = clean_body_text(entry["pdf_text"])
            results.append(entry)

        return {"query": query, "dimension": dimension, "results": results}


class SerpAPISearchTool:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        max_results: int = 8,
        top_k_per_query: int = 5,
    ) -> None:
        self._api_key = api_key or os.environ.get("SERPAPI_API_KEY")
        if not self._api_key:
            raise ValueError("SERPAPI_API_KEY environment variable is required")
        self.max_results = max_results
        self.top_k_per_query = top_k_per_query

    async def search(self, query: str, topic: str, dimension: str | None = None) -> dict[str, Any]:
        logger.info("Searching SerpAPI for query=%s", query)
        params = {
            "engine": "google",
            "q": query,
            "api_key": self._api_key,
            "num": self.max_results,
        }

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get("https://serpapi.com/search.json", params=params)
            response.raise_for_status()
            payload = response.json()

        organic_results = payload.get("organic_results", [])[: self.top_k_per_query]
        results: list[dict[str, Any]] = []
        for item in organic_results:
            url = item.get("link", "")
            snippet = item.get("snippet", "") or item.get("snippet_highlighted_words", [])
            if isinstance(snippet, list):
                snippet = " ".join(str(part) for part in snippet)

            entry = {
                "topic": topic,
                "dimension": dimension or "",
                "query": query,
                "title": item.get("title", ""),
                "url": url,
                "score": None,
                "published_date": item.get("date"),
                "snippet": snippet,
                "raw_content": "",
            }
            entry["body"] = clean_body_text(snippet)

            if _looks_like_pdf(url):
                entry["pdf_text"] = await fetch_pdf_text(url)
                if entry["pdf_text"]:
                    entry["body"] = clean_body_text(entry["pdf_text"])

            results.append(entry)

        return {"query": query, "dimension": dimension, "results": results}


def create_search_tool(*, max_results: int = 8, top_k_per_query: int = 5):
    provider = os.environ.get("SEARCH_PROVIDER", "").lower().strip()

    if provider == "serpapi" or (not os.environ.get("TAVILY_API_KEY") and os.environ.get("SERPAPI_API_KEY")):
        return SerpAPISearchTool(
            max_results=max_results,
            top_k_per_query=top_k_per_query,
        )

    return TavilySearchTool(
        max_results=max_results,
        top_k_per_query=top_k_per_query,
    )


def clean_body_text(text: str, *, max_chars: int = 12000) -> str:
    normalized = " ".join((text or "").split())
    return normalized[:max_chars]


def _looks_like_pdf(url: str) -> bool:
    path = urlparse(url).path.lower()
    return path.endswith(".pdf")


async def fetch_pdf_text(url: str, *, timeout: float = 20.0, max_chars: int = 16000) -> str:
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
        return extract_pdf_text(response.content, max_chars=max_chars)
    except Exception as exc:
        logger.warning("Failed to read PDF %s: %s", url, exc)
        return ""


def extract_pdf_text(pdf_bytes: bytes, *, max_chars: int = 16000) -> str:
    chunks: list[str] = []
    current_length = 0
    with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
        for page in document:
            text = page.get_text("text")
            chunks.append(text)
            current_length += len(text)
            if current_length >= max_chars:
                break
    return "\n".join(chunks)[:max_chars]
