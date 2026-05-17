"""關鍵字觸發的本機直接執行（不依賴 MCP / 外掛）。"""

from __future__ import annotations

import html
import json
import re

from hermers.executor import HermesExecutor, RunResult
from hermers.paths import posts_dir
from hermers.site import rebuild_index, refresh_dist_article_pages

_BEAUTIFY = re.compile(
    r"美化|優化\s*(?:網站|ui|介面|版面|樣式)|改進\s*(?:ui|版面|樣式)|"
    r"(?:調整|改).{0,4}(?:ui|版面|樣式)",
    re.I,
)
_REMOVE = re.compile(r"(?:移除|刪除|去掉|拿掉)(?:文章|貼文|這篇|這則|那篇)?", re.I)
_DEPLOY = re.compile(r"部署|上線|cloudflare|發布網站", re.I)
_POST_ID = re.compile(r"\b(20\d{6}(?:-\d{6})?[-\w\u4e00-\u9fff]+)\b", re.I)


def beautify_site_ui() -> RunResult:
    refresh_dist_article_pages()
    rebuild_index()
    return RunResult(
        True,
        "<b>已在本機美化剪報站</b>\n"
        "已刷新文章頁皮膚並重建 <code>dist/index.html</code>。\n"
        "若要同步到 Cloudflare，請傳 <code>/deploy</code> 或說「部署」。",
    )


def _remove_post_files(post_id: str) -> bool:
    root = posts_dir()
    html_path = root / f"{post_id}.html"
    json_path = root / f"{post_id}.json"
    if not html_path.is_file():
        return False
    html_path.unlink()
    if json_path.is_file():
        json_path.unlink()
    return True


def _find_posts_by_title(fragment: str) -> list[str]:
    fragment = fragment.strip().lower()
    if len(fragment) < 2:
        return []
    hits: list[str] = []
    for meta_path in posts_dir().glob("*.json"):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        title = str(meta.get("title") or "").lower()
        if fragment in title or fragment in meta_path.stem.lower():
            hits.append(meta_path.stem)
    return hits


def remove_articles(text: str) -> RunResult:
    ids = list(dict.fromkeys(_POST_ID.findall(text)))
    if not ids:
        m = re.search(r"[「『\"](.+?)[」』\"]", text)
        if m:
            ids = _find_posts_by_title(m.group(1))
        else:
            tail = re.sub(_REMOVE, "", text).strip()
            if len(tail) >= 2:
                ids = _find_posts_by_title(tail[:80])

    if not ids:
        return RunResult(
            False,
            "<b>找不到要刪的文章</b>\n"
            "請附上草稿 ID（如 <code>20260516-xxxx</code>）或標題關鍵字。",
        )

    removed: list[str] = []
    for post_id in ids[:5]:
        if _remove_post_files(post_id):
            removed.append(post_id)

    if not removed:
        return RunResult(False, "<b>刪除失敗</b>：找不到對應的 dist/posts 檔案。")

    rebuild_index()
    return RunResult(
        True,
        "<b>已移除文章</b>\n"
        + "\n".join(f"• <code>{html.escape(i)}</code>" for i in removed)
        + "\n\n已重建首頁。上線請傳 <code>/deploy</code>。",
    )


def try_local_action(text: str) -> RunResult | None:
    t = (text or "").strip()
    if not t or t.startswith("/"):
        return None

    if _REMOVE.search(t):
        return remove_articles(t)
    if _BEAUTIFY.search(t):
        return beautify_site_ui()
    if _DEPLOY.search(t):
        return HermesExecutor().deploy()

    return None
