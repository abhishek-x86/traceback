

from __future__ import annotations

import json
import os
import urllib.request
from typing import Optional

TAVILY_API_ENDPOINT = "https://api.tavily.com/search"


def search_error_context(
    exception_type: str,
    exception_message: str,
    code_snippet: str = "",
    timeout: float = 6.0,
) -> Optional[str]:
    """Query Tavily Search API for solutions to the specific exception.

    Returns a markdown-formatted string with top external context, or None
    if TAVILY_API_KEY is unset, search fails, or yields empty results.
    """
    api_key = (
        os.environ.get("TAVILY_API_KEY")
        or os.environ.get("TRACEBACK_TAVILY_KEY")
    )
    if not api_key:
        return None

    query = f"Python {exception_type}: {exception_message} fix solution"

    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "include_answer": True,
        "max_results": 2,
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            TAVILY_API_ENDPOINT,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status != 200:
                return None
            body = json.loads(response.read().decode("utf-8"))

        results = body.get("results", [])
        answer = body.get("answer")

        snippets = []
        if answer:
            snippets.append(f"**Tavily Summary:** {answer}")

        for item in results:
            title = item.get("title", "Resource")
            content = item.get("content", "")
            url = item.get("url", "")
            if content:
                snippets.append(f"**[{title}]({url}):** {content[:350]}...")

        if not snippets:
            return None

        return "\n\n".join(snippets)

    except Exception:
        return None
