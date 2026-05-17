"""無 LLM 時的規則路由（仍會直接執行，不建任務檔）。"""

from __future__ import annotations

import re

from hermers.agent.tools import extract_urls, run_tool
from hermers.url_policy import is_own_site_url
from hermers.executor import RunResult

_DEPLOY = re.compile(r"部署|上線|cloudflare|發布網站", re.I)
_PUBLISH = re.compile(r"推送|push|publish|上傳\s*git", re.I)
_PIPELINE = re.compile(r"剪報|digest|pipeline|rss|熱門", re.I)
# 僅明確查狀態；勿用單字「網站」（會誤殺「美化網站 UI」等任務句）
_STATUS = re.compile(
    r"^(?:/status|狀態|系統狀態|健康檢查|health|status)\s*$|"
    r"(?:查|看|顯示).{0,6}(?:系統)?狀態",
    re.I,
)
_SITE_QUERY = re.compile(
    r"(?:"
    r"網站\s*網址|網址\s*(?:多少|是什麼|在哪|幾號)|"
    r"(?:有|給|告訴).{0,4}網址|什麼\s*網址|對外\s*網址|"
    r"site\s*url|workers\.dev|"
    r"(?:網站|站).{0,4}(?:上線|好了|連得上|能開)|"
    r"上線了嗎|部署好了嗎"
    r")",
    re.I,
)
_HELP = re.compile(r"幫我做什麼|能做什麼|可以做什麼|如何使用|怎麼用|說明|help|指令", re.I)


def wants_site_url_info(text: str) -> bool:
    return bool(_SITE_QUERY.search(text))


def route(text: str) -> RunResult | None:
    t = (text or "").strip()
    if not t or t.startswith("/"):
        return None

    urls = extract_urls(t)
    if urls and not _PIPELINE.search(t):
        news_urls = [u for u in urls if not is_own_site_url(u)]
        if news_urls:
            return run_tool(
                "ingest_news_url",
                {
                    "url": news_urls[0],
                    "push": bool(_PUBLISH.search(t) or _DEPLOY.search(t)),
                },
            )
        if urls and all(is_own_site_url(u) for u in urls):
            return run_tool("site_url_info", {})

    if _DEPLOY.search(t):
        return run_tool("deploy_site", {})
    if _PUBLISH.search(t):
        return run_tool("publish_git", {})
    if _PIPELINE.search(t):
        return run_tool("run_digest_pipeline", {"push": bool(_PUBLISH.search(t))})
    if _STATUS.search(t):
        return run_tool("system_status", {})
    if wants_site_url_info(t):
        return run_tool("site_url_info", {})
    if _HELP.search(t):
        return run_tool("list_capabilities", {})

    return None
