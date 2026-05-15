from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path

from hermers.paths import dist_dir, pending_dir, posts_dir


def rebuild_index() -> None:
    posts_dir().mkdir(parents=True, exist_ok=True)
    entries: list[dict] = []
    for path in sorted(posts_dir().glob("*.html"), reverse=True):
        meta_path = path.with_suffix(".json")
        title = path.stem
        published = ""
        domain = ""
        if meta_path.is_file():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            title = meta.get("title") or title
            published = meta.get("approved_at") or ""
            domain = meta.get("domain_name") or ""
        entries.append(
            {
                "href": f"posts/{path.name}",
                "title": title,
                "published": published,
                "domain": domain,
            }
        )

    pending_count = len(list(pending_dir().glob("*/meta.json"))) if pending_dir().is_dir() else 0
    items_html = ""
    if not entries:
        items_html = "<p>尚無已發布文章。請先審核通過待審草稿。</p>"
    else:
        for e in entries:
            date = e["published"][:10] if e["published"] else ""
            tag = html.escape(e["domain"]) if e["domain"] else ""
            items_html += (
                f'<li><a href="{html.escape(e["href"])}">{html.escape(e["title"])}</a>'
                f' <span class="meta">{html.escape(tag)} {html.escape(date)}</span></li>\n'
            )

    content = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Hermers 剪報站</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 44rem; margin: 2rem auto; padding: 0 1rem; line-height: 1.6; }}
    h1 {{ font-size: 1.4rem; }}
    .badge {{ background: #f4f4f5; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.85rem; }}
    ul {{ padding-left: 1.2rem; }}
    .meta {{ color: #666; font-size: 0.85rem; }}
  </style>
</head>
<body>
  <h1>Hermers 剪報站</h1>
  <p class="badge">待審：{pending_count} 則 · 已發布：{len(entries)} 則</p>
  <p>本頁僅含<strong>已審核通過</strong>的文章。待審內容請開啟 <code>staging/review.html</code>。</p>
  <ul>
{items_html}  </ul>
  <p><small>更新時間（UTC） {html.escape(datetime.utcnow().isoformat(timespec="seconds"))}</small></p>
</body>
</html>
"""
    dist_dir().mkdir(parents=True, exist_ok=True)
    (dist_dir() / "index.html").write_text(content, encoding="utf-8")


def write_review_page() -> Path:
    from hermers.paths import staging_dir

    staging_dir().mkdir(parents=True, exist_ok=True)
    rows = []
    if pending_dir().is_dir():
        for meta_path in sorted(pending_dir().glob("*/meta.json")):
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            draft_id = meta["id"]
            title = html.escape(meta.get("title") or draft_id)
            url = html.escape(meta.get("url") or "")
            domain = html.escape(meta.get("domain_name") or "")
            rel = html.escape(f"pending/{draft_id}/draft.html")
            rows.append(
                f"<tr><td>{domain}</td><td><a href=\"{rel}\">{title}</a></td>"
                f'<td><a href="{url}">原文</a></td>'
                f"<td><code>{html.escape(draft_id)}</code></td></tr>"
            )
    body = "\n".join(rows) if rows else "<tr><td colspan=\"4\">目前沒有待審草稿。請執行 pipeline.bat。</td></tr>"
    page = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Hermers 待審清單</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 56rem; margin: 2rem auto; padding: 0 1rem; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border-bottom: 1px solid #ddd; padding: 0.5rem; text-align: left; vertical-align: top; }}
    code {{ font-size: 0.85rem; }}
    .help {{ background: #f8fafc; padding: 1rem; border-radius: 8px; }}
  </style>
</head>
<body>
  <h1>待審清單</h1>
  <div class="help">
    <p>1. 點草稿預覽 · 2. 不滿意可在 Cursor 改 <code>staging/pending/…/draft.html</code></p>
    <p>3. 通過：<code>approve.bat 草稿ID</code> · 4. 拒絕：<code>reject.bat 草稿ID</code> · 5. 滿意後 <code>publish.bat</code> 推 GitHub</p>
  </div>
  <table>
    <thead><tr><th>領域</th><th>草稿</th><th>原文</th><th>ID（給 approve）</th></tr></thead>
    <tbody>
{body}
    </tbody>
  </table>
</body>
</html>
"""
    out = staging_dir() / "review.html"
    out.write_text(page, encoding="utf-8")
    return out
