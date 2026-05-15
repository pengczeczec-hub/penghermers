from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path

from hermers.discover import FeedItem
from hermers.fetch import ArticleExtract


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

請在通過審核前，視需要改寫 `draft.html`（繁體中文、剪報體、保留來源連結）。

## 擷取摘要（自動）

{summary[:2000]}
"""


def _draft_html(meta: dict, extract: ArticleExtract) -> str:
    title = html.escape(meta["title"])
    url = html.escape(meta["url"])
    domain = html.escape(meta["domain_name"])
    body = "".join(f"<p>{html.escape(p)}</p>" for p in extract.paragraphs[:8])
    if not body:
        body = "<p><em>（未能擷取內文，請在 Cursor 中依連結手動撰寫。）</em></p>"
    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 42rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.65; }}
    .tag {{ color: #666; font-size: 0.9rem; }}
    a {{ color: #06c; }}
  </style>
</head>
<body>
  <p class="tag">{domain} · 待審草稿</p>
  <h1>{title}</h1>
  <p>來源：<a href="{url}" rel="noopener noreferrer">{url}</a></p>
  <hr />
  {body}
  <hr />
  <p><small>自動擷取摘要；審核通過後才會進入 dist/ 並可推送 GitHub。</small></p>
</body>
</html>
"""
