from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path

from hermers.i18n_ui import (
    i18n_runtime_script,
    lang_switcher_css,
    lang_switcher_html,
    public_base_url,
    seo_block,
    strip_empty_seo_placeholders,
)
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
            lang_switcher_css(),
            css_shell(narrow=False),
            css_index_specific(),
        ]
    )
    base = public_base_url()
    index_canonical = f"{base}/" if base else ""
    og_title = "Hermers 剪報站 | Hermers Digest"
    desc_zh = "已審核通過的剪報索引，版面清楚、來源可追溯。"
    desc_en = "Curated digest of approved clippings with clear layout and traceable sources."
    head_seo = seo_block(
        canonical_url=index_canonical,
        og_title=og_title,
        description_zh=desc_zh,
        description_en=desc_en,
    )
    empty_msg = (
        "<p class=\"empty\"><span data-i18n-zh=\"尚無已發布文章。請先完成待審流程。\""
        ' data-i18n-en="No published items yet. Complete the review workflow first."></span></p>'
    )
    list_block = (
        empty_msg
        if not entries
        else f"<ul class=\"post-list\">\n{items_html}</ul>"
    )
    content = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="color-scheme" content="light" />
{head_seo}  <title>{html.escape(og_title)}</title>
  <style>{css}
  </style>
</head>
<body>
  {lang_switcher_html()}
  <main>
    <header class="masthead">
      <h1><span data-i18n-zh="Hermers 剪報站" data-i18n-en="Hermers Digest"></span></h1>
      <p class="sub"><span data-i18n-zh="已審核通過的剪報條目；版面清楚、來源可追溯。"
        data-i18n-en="Approved clippings only—clean layout with traceable sources."></span></p>
      <div class="stats">
        <span class="pill"><span data-i18n-zh="待審" data-i18n-en="Pending"></span>
          <strong>{pending_count}</strong>
          <span data-i18n-zh="則" data-i18n-en="items"></span></span>
        <span class="pill"><span data-i18n-zh="已發布" data-i18n-en="Published"></span>
          <strong>{len(entries)}</strong>
          <span data-i18n-zh="則" data-i18n-en="items"></span></span>
      </div>
    </header>
    <p class="sub" style="margin-bottom: 1rem"><span data-i18n-zh="本頁僅列出已上線文章；草稿與待審在管理流程／本機 staging 目錄處理，不會出現於此。"
      data-i18n-en="This page lists live posts only; drafts and pending items stay in staging and admin flows."></span></p>
    <div class="list-wrap">
      {list_block}
    </div>
    <footer class="time"><span data-i18n-zh="更新時間（UTC）·" data-i18n-en="Last update (UTC)·"></span>
      {html.escape(datetime.utcnow().isoformat(timespec="seconds"))}</footer>
  </main>
{i18n_runtime_script()}
</body>
</html>
"""
    content = strip_empty_seo_placeholders(content)
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
            src_lbl = (
                '<span data-i18n-zh="原文" data-i18n-en="Article"></span>'
            )
            rows.append(
                f"<tr><td>{domain}</td><td><a href=\"{rel}\">{title}</a></td>"
                f'<td><a href="{url}">{src_lbl}</a></td>'
                f"<td><code>{html.escape(draft_id)}</code></td></tr>"
            )
    body = (
        "\n".join(rows)
        if rows
        else '<tr><td colspan="4"><span data-i18n-zh="目前沒有待審草稿。請跑剪報／擷取流程（例如 pipeline）。"'
        ' data-i18n-en="No pending drafts. Run the ingest / digest pipeline."></span></td></tr>'
    )
    css_r = "".join(
        [css_base(), lang_switcher_css(), css_shell(narrow=False), css_review_specific()]
    )
    rev_title = "Hermers 待審清單 | Hermers Review Queue"
    rev_canonical = ""  # 審核頁留在 staging，不強制對外 canonical
    head_seo_r = seo_block(
        canonical_url=rev_canonical,
        og_title=rev_title,
        description_zh="待審剪報草稿清單（本機 staging）。",
        description_en="Pending clipping drafts (local staging review).",
    )
    page = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="color-scheme" content="light" />
{head_seo_r}  <title>{html.escape(rev_title)}</title>
  <style>{css_r}
  </style>
</head>
<body>
  {lang_switcher_html()}
  <main>
    <h1 class="page-title"><span data-i18n-zh="待審清單" data-i18n-en="Review queue"></span></h1>
    <div class="help">
      <p><span data-i18n-zh="1. 點「草稿」預覽 · 2. 需要潤稿時編輯"
        data-i18n-en="1. Open “Draft” to preview · 2. Edit when needed:"></span>
        <code>staging/pending/&lt;草稿ID&gt;/draft.html</code></p>
      <p><span data-i18n-zh="3. 通過："
        data-i18n-en="3. Approve:"></span> <code>approve.bat</code>／<code>hermes-review approve</code>
        <span data-i18n-zh="· 4. 拒絕：" data-i18n-en=" · 4. Reject:"></span> <code>reject.bat</code>
        <span data-i18n-zh="· 5. 上線前" data-i18n-en=" · 5. Before go-live"></span> <code>publish.bat</code>
        <span data-i18n-zh="推送 GitHub" data-i18n-en="push to GitHub"></span></p>
    </div>
    <div class="table-card">
      <table>
        <thead><tr>
          <th><span data-i18n-zh="領域" data-i18n-en="Beat"></span></th>
          <th><span data-i18n-zh="草稿" data-i18n-en="Draft"></span></th>
          <th><span data-i18n-zh="原文" data-i18n-en="Source"></span></th>
          <th><span data-i18n-zh="ID（給 approve）" data-i18n-en="ID (for approve)"></span></th>
        </tr></thead>
        <tbody>
{body}
        </tbody>
      </table>
    </div>
  </main>
{i18n_runtime_script()}
</body>
</html>
"""
    page = strip_empty_seo_placeholders(page)
    out = staging_dir() / "review.html"
    out.write_text(page, encoding="utf-8")
    return out
