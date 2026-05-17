from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path

from hermers.discover import FeedItem
from hermers.fetch import ArticleExtract
from hermers.i18n_ui import i18n_runtime_script, lang_switcher_css, lang_switcher_html, seo_block
from hermers.static_skin import css_article_specific, css_base, css_shell
from hermers.translate_body import zh_paragraphs_from_extract, zh_title_from_extract


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

請在通過審核前，視需要改寫同資料夾內 `draft.html`（`.hermers-i18n-zh` 為繁體、`hermers-i18n-en` 為英文摘要；剪報體、保留來源連結）。

## 擷取摘要（自動）

{summary[:2000]}
"""


def _paragraph_chunks_to_ps(parts: list[str]) -> str:
    chunks: list[str] = []
    for raw in parts:
        for piece in (s.strip() for s in raw.split("\n\n")):
            if piece:
                chunks.append(f"<p>{html.escape(piece)}</p>")
    return "".join(chunks)


def _bilingual_headings(title_raw: str) -> tuple[str, str]:
    """回傳 (title_zh_esc, title_en_esc)。中文來源標題時兩側先相同，留待人工補英文。"""
    esc = html.escape(title_raw)
    if any("\u4e00" <= c <= "\u9fff" for c in title_raw):
        return esc, esc
    zh_plain = zh_title_from_extract(title_raw) or title_raw
    return html.escape(zh_plain), esc


def render_article_page(
    meta: dict,
    *,
    body_block_html: str,
    pending: bool,
    title_raw: str | None = None,
) -> str:
    """共用單頁版面：RSS 草稿、手動重建或升級 legacy dist 文章皆可呼叫。"""
    t_raw = title_raw if title_raw is not None else str(meta["title"])
    title_zh_esc, title_en_esc = _bilingual_headings(t_raw)
    url = html.escape(meta["url"])
    domain = html.escape(meta["domain_name"])
    if pending:
        desc_zh = f"「{t_raw}」剪報草稿（待審），來源連結於文內。"
        desc_en = f'Clipping draft (pending): "{t_raw}". Source link inside.'
        eyebrow = f'{domain} · <span data-i18n-zh="待審草稿" data-i18n-en="Pending draft"></span>'
        foot = (
            '<span data-i18n-zh="自動擷取摘要；通過審核後會進入 dist/ 並可部署上線。"'
            ' data-i18n-en="Auto-extracted summary; after approval this goes to dist/ for deploy."></span>'
        )
    else:
        desc_zh = f"「{t_raw}」剪報（已發布），來源連結於文內。"
        desc_en = f'Published clipping: "{t_raw}". Source link inside.'
        eyebrow = f'{domain} · <span data-i18n-zh="已發布" data-i18n-en="Published"></span>'
        foot = (
            '<span data-i18n-zh="已審核發布於 Hermers 剪報站；可追溯原文連結。"'
            ' data-i18n-en="Published on Hermers Digest; original source linked above."></span>'
        )
    head_seo = seo_block(
        canonical_url="__CANONICAL_URL__",
        og_title=t_raw,
        description_zh=desc_zh[:220],
        description_en=desc_en[:220],
        og_type="article",
    )
    css_full = "".join(
        [css_base(), lang_switcher_css(), css_shell(narrow=True), css_article_specific()]
    )
    title_tab = html.escape(t_raw)
    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="color-scheme" content="light" />
{head_seo}  <title>{title_tab}</title>
  <style>{css_full}
  </style>
</head>
<body>
  {lang_switcher_html(compact=True)}
  <main>
    <article class="prose">
      <p class="eyebrow">{eyebrow}</p>
      <h1><span class="hermers-i18n-zh">{title_zh_esc}</span><span class="hermers-i18n-en">{title_en_esc}</span></h1>
      <div class="source-box"><span data-i18n-zh="來源：" data-i18n-en="Source:"></span><a href="{url}" rel="noopener noreferrer">{url}</a></div>
      <hr />
{body_block_html}
      <footer class="note">{foot}</footer>
    </article>
  </main>
{i18n_runtime_script()}
</body>
</html>
"""


def _draft_html(meta: dict, extract: ArticleExtract) -> str:
    title_raw = meta["title"]
    paras_en = extract.paragraphs[:8]
    body_en = _paragraph_chunks_to_ps(list(paras_en))
    body_zh = _paragraph_chunks_to_ps(zh_paragraphs_from_extract(paras_en)) if paras_en else ""
    empty_inner = (
        "<p><em><span data-i18n-zh=\"（未能擷取內文，請依上方原文連結手動撰寫後再送審。）\""
        ' data-i18n-en="(No body extracted—please draft from the source link above before review.)">'
        "</span></em></p>"
    )
    if not body_en:
        body_zh = empty_inner
        body_en = empty_inner
    body = f"""      <div class="hermers-i18n-zh">{body_zh}</div>
      <div class="hermers-i18n-en">{body_en}</div>
"""
    return render_article_page(meta, body_block_html=body, pending=True, title_raw=title_raw)


def legacy_minimal_article_inner_body(page_html: str) -> str | None:
    """從早期 system-ui 版型擷取 <hr /> 之間正文（連續段落 HTML）。"""
    parts = page_html.split("<hr />")
    if len(parts) < 3:
        return None
    inner = parts[1].strip()
    return inner if inner else None
