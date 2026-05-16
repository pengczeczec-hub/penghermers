"""無 LLM 時的規則路由（仍會直接執行，不建任務檔）。"""

from __future__ import annotations

import re

from hermers.agent.tools import extract_urls, run_tool
from hermers.executor import RunResult

_DEPLOY = re.compile(r"部署|上線|cloudflare|發布網站", re.I)
_PUBLISH = re.compile(r"推送|push|publish|上傳\s*git", re.I)
_PIPELINE = re.compile(r"剪報|digest|pipeline|rss|熱門", re.I)
_STATUS = re.compile(r"狀態|status|健康", re.I)
_SITE = re.compile(r"網址|網站|域名|有網址|上線了嗎|部署好了嗎|workers\.dev", re.I)
_HELP = re.compile(r"幫我做什麼|能做什麼|可以做什麼|如何使用|怎麼用|說明|help|指令", re.I)


def route(text: str) -> RunResult | None:
    t = (text or "").strip()
    if not t or t.startswith("/"):
        return None

    urls = extract_urls(t)
    if urls and not _PIPELINE.search(t):
        return run_tool("ingest_news_url", {"url": urls[0], "push": bool(_PUBLISH.search(t) or _DEPLOY.search(t))})

    if _DEPLOY.search(t):
        return run_tool("deploy_site", {})
    if _PUBLISH.search(t):
        return run_tool("publish_git", {})
    if _PIPELINE.search(t):
        return run_tool("run_digest_pipeline", {"push": bool(_PUBLISH.search(t))})
    if _STATUS.search(t):
        return run_tool("system_status", {})
    if _SITE.search(t):
        return run_tool("site_url_info", {})
    if _HELP.search(t):
        return run_tool("list_capabilities", {})

    return None
