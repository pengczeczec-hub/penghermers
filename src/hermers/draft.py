from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path

from hermers.discover import FeedItem
from hermers.fetch import ArticleExtract
from hermers.i18n_ui import i18n_runtime_script, lang_switcher_css, lang_switcher_html, seo_block
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
    title_raw = meta["title"]
    title_esc = html.escape(title_raw)
    url = html.escape(meta["url"])
    domain = html.escape(meta["domain_name"])
    body = "".join(f"<p>{html.escape(p)}</p>" for p in extract.paragraphs[:8])
    if not body:
        body = (
            "<p><em><span data-i18n-zh=\"（未能擷取內文，請依上方原文連結手動撰寫後再送審。）\""
            ' data-i18n-en="(No body extracted—please draft from the source link above before review.)">'
            "</span></em></p>"
        )
    desc_zh = f"「{title_raw}」剪報草稿（待審），來源連結於文內。"
    desc_en = f'Clipping draft (pending): "{title_raw}". Source link inside.'
    head_seo = seo_block(
        canonical_url="__CANONICAL_URL__",
        og_title=title_raw,
        description_zh=desc_zh[:220],
        description_en=desc_en[:220],
        og_type="article",
    )
    css_a = "".join(
        [css_base(), lang_switcher_css(), css_shell(narrow=True), css_article_specific()]
    )
    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="color-scheme" content="light" />
{head_seo}  <title>{title_esc}</title>
  <style>{css_a}
  </style>
</head>
<body>
  {lang_switcher_html(compact=True)}
  <main>
    <article class="prose">
      <p class="eyebrow">{domain} · <span data-i18n-zh="待審草稿" data-i18n-en="Pending draft"></span></p>
      <h1>{title_esc}</h1>
      <div class="source-box"><span data-i18n-zh="來源：" data-i18n-en="Source:"></span><a href="{url}" rel="noopener noreferrer">{url}</a></div>
      <hr />
      {body}
      <footer class="note"><span data-i18n-zh="自動擷取摘要；通過審核後會進入 dist/ 並可部署上線。"
        data-i18n-en="Auto-extracted summary; after approval this goes to dist/ for deploy."></span></footer>
    </article>
  </main>
{i18n_runtime_script()}
</body>
</html>
"""
