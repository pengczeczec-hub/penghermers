from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path

from hermers.discover import FeedItem
from hermers.fetch import ArticleExtract
from hermers.static_skin import css_article_specific, css_base, css_shell


def write_pending(
    folder: Path,
    *,
    item: FeedItem,
    extract: ArticleExtract,
    draft_id: str,
) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    summary = "\n\n".join(extract.paragraphs[:3])
    meta = {
        "id": draft_id,
        "status": "pending",
        "domain_id": item.domain_id,
        "domain_name": item.domain_name,
        "title": extract.title or item.title,
        "source_title": item.title,
        "url": item.url,
        "rss_source": item.source,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (folder / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (folder / "CURSOR_TASK.md").write_text(
        _cursor_task(meta, summary), encoding="utf-8"
    )
    (folder / "draft.html").write_text(
        _draft_html(meta, extract), encoding="utf-8"
    )


def _cursor_task(meta: dict, summary: str) -> str:
    return f"""# Cursor 潤稿任務（可選）

待審草稿：`{meta["id"]}`
原文：{meta["url"]}

請在通過審核前，視需要改寫同資料夾內 `draft.html`（繁體中文、剪報體、保留來源連結）。

## 擷取摘要（自動）

{summary[:2000]}
"""


def _draft_html(meta: dict, extract: ArticleExtract) -> str:
    title = html.escape(meta["title"])
    url = html.escape(meta["url"])
    domain = html.escape(meta["domain_name"])
    body = "".join(f"<p>{html.escape(p)}</p>" for p in extract.paragraphs[:8])
    if not body:
        body = "<p><em>（未能擷取內文，請依上方原文連結手動撰寫後再送審。）</em></p>"
    css_a = "".join([css_base(), css_shell(narrow=True), css_article_specific()])
    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="color-scheme" content="light" />
  <title>{title}</title>
  <style>{css_a}
  </style>
</head>
<body>
  <main>
    <article class="prose">
      <p class="eyebrow">{domain} · 待審草稿</p>
      <h1>{title}</h1>
      <div class="source-box">來源：<a href="{url}" rel="noopener noreferrer">{url}</a></div>
      <hr />
      {body}
      <footer class="note">自動擷取摘要；通過審核後會進入 dist/ 並可部署上線。</footer>
    </article>
  </main>
</body>
</html>
"""
