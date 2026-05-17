"""對外網站即時連線檢查（不依賴本機 published 旗標）。"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

import httpx

from hermers.env_load import load_dotenv

_DEFAULT_SITE = "https://penghermers.pengczeczec.workers.dev/"

_PLACEHOLDER_MARKERS = (
    "hello world",
    "there is nothing here yet",
    "nothing here yet",
)


@dataclass(frozen=True)
class SiteLiveCheck:
    url: str
    online: bool
    status_code: int | None
    detail: str
    published_count: int | None = None


def public_site_url() -> str:
    load_dotenv()
    site = os.environ.get("SITE_PUBLIC_URL", "").strip()
    if site:
        return site if site.endswith("/") else f"{site}/"
    return _DEFAULT_SITE


def _normalize_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return public_site_url()
    if not u.startswith(("http://", "https://")):
        u = "https://" + u
    return u if u.endswith("/") else f"{u}/"


def _looks_live(body: str) -> bool:
    if not body or len(body) < 80:
        return False
    lower = body.lower()
    for marker in _PLACEHOLDER_MARKERS:
        if marker in lower:
            return False
    if "hermers" in lower and ("剪報" in body or 'href="posts/' in body):
        return True
    if re.search(r"已發布[：:]\s*\d+", body):
        return True
    if 'href="posts/' in body:
        return True
    return False


def _parse_published_count(body: str) -> int | None:
    m = re.search(r"已發布[：:]\s*(\d+)", body)
    if m:
        return int(m.group(1))
    return None


def check_site_live(url: str | None = None, *, timeout: float = 8.0) -> SiteLiveCheck:
    target = _normalize_url(url or public_site_url())
    try:
        with httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "Hermers/1.0 (site-live-check)"},
        ) as client:
            resp = client.get(target)
    except httpx.HTTPError as exc:
        return SiteLiveCheck(
            url=target,
            online=False,
            status_code=None,
            detail=f"無法連線：{exc}",
        )

    body = resp.text or ""
    online = resp.status_code == 200 and _looks_live(body)
    count = _parse_published_count(body) if online else None

    if online:
        detail = f"HTTP {resp.status_code}，剪報站可讀"
        if count is not None:
            detail += f"（已發布 {count} 則）"
    elif resp.status_code == 200:
        detail = f"HTTP 200，但內容仍像佔位頁（非正式剪報站）"
    else:
        detail = f"HTTP {resp.status_code}"

    return SiteLiveCheck(
        url=target,
        online=online,
        status_code=resp.status_code,
        detail=detail,
        published_count=count,
    )


def site_live_html_block(check: SiteLiveCheck) -> str:
    import html as html_mod

    url = html_mod.escape(check.url)
    if check.online:
        return (
            f"✅ <b>已上線</b>（即時檢查）\n<code>{url}</code>\n"
            f"{html_mod.escape(check.detail)}"
        )
    return (
        f"⚠️ <b>無法確認上線</b>（即時檢查）\n<code>{url}</code>\n"
        f"{html_mod.escape(check.detail)}"
    )
