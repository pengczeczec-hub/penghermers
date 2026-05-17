from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path

from hermers.paths import dist_dir, pending_dir, posts_dir
from hermers.static_skin import css_base, css_index_specific, css_review_specific, css_shell


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
    for e in entries:
        date = e["published"][:10] if e["published"] else ""
        tag = html.escape(e["domain"]) if e["domain"] else ""
        sep = " · " if tag and date else ""
        meta_line = f"{tag}{sep}{html.escape(date)}".strip()
        meta_block = (
            f'<span class="meta">{meta_line}</span>\n'
            if meta_line
            else '<span class="meta">—</span>\n'
        )
        items_html += (
            f'<li><a href="{html.escape(e["href"])}">{html.escape(e["title"])}</a>{meta_block}</li>\n'
        )

    css = "".join(
        [
            css_base(),
            css_shell(narrow=False),
            css_index_specific(),
        ]
    )

    content = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="color-scheme" content="light" />
  <title>Hermers 剪報站</title>
  <style>{css}
  </style>
</head>
<body>
  <main>
    <header class="masthead">
      <h1>Hermers 剪報站</h1>
      <p class="sub">已審核通過的剪報條目；版面清楚、來源可追溯。</p>
      <div class="stats">
        <span class="pill">待審 <strong>{pending_count}</strong> 則</span>
        <span class="pill">已發布 <strong>{len(entries)}</strong> 則</span>
      </div>
    </header>
    <p class="sub" style="margin-bottom: 1rem">本頁僅列出已上線文章；草稿與待審在管理流程／本機 staging 目錄處理，不會出現於此。</p>
    <div class="list-wrap">
      {"<p class=\"empty\">尚無已發布文章。請先完成待審流程。</p>" if not entries else f"<ul class=\"post-list\">\n{items_html}</ul>"}
    </div>
    <footer class="time">更新時間（UTC）· {html.escape(datetime.utcnow().isoformat(timespec="seconds"))}</footer>
  </main>
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
    body = "\n".join(rows) if rows else "<tr><td colspan=\"4\">目前沒有待審草稿。請跑剪報／擷取流程（例如 pipeline）。</td></tr>"
    css_r = "".join([css_base(), css_shell(narrow=False), css_review_specific()])
    page = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="color-scheme" content="light" />
  <title>Hermers 待審清單</title>
  <style>{css_r}
  </style>
</head>
<body>
  <main>
    <h1 class="page-title">待審清單</h1>
    <div class="help">
      <p>1. 點「草稿」預覽 · 2. 需要潤稿時編輯 <code>staging/pending/&lt;草稿ID&gt;/draft.html</code></p>
      <p>3. 通過：<code>approve.bat</code>／<code>hermes-review approve</code> · 4. 拒絕：<code>reject.bat</code> · 5. 上線前 <code>publish.bat</code> 推送 GitHub</p>
    </div>
    <div class="table-card">
      <table>
        <thead><tr><th>領域</th><th>草稿</th><th>原文</th><th>ID（給 approve）</th></tr></thead>
        <tbody>
{body}
        </tbody>
      </table>
    </div>
  </main>
</body>
</html>
"""
    out = staging_dir() / "review.html"
    out.write_text(page, encoding="utf-8")
    return out
