from __future__ import annotations

import html
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from hermers.draft import (
    bilingual_headings_plain,
    build_bilingual_body_block_from_fragment,
    legacy_minimal_article_inner_body,
    render_article_page,
)
from hermers.i18n_ui import (
    i18n_runtime_script,
    lang_switcher_css,
    lang_switcher_html,
    polish_published_post,
    public_base_url,
    seo_block,
    strip_empty_seo_placeholders,
)
from hermers.paths import dist_dir, pending_dir, posts_dir
from hermers.static_skin import css_base, css_index_specific, css_review_specific, css_shell

# 首頁分類順序（對應 domains.yaml 的 section_*）；舊稿無欄位時依 domain_id 回退。
_SECTION_FALLBACK: dict[str, tuple[str, str]] = {
    "tw_market_extra": ("重大頭條", "Major headlines"),
    "tw_stock": ("市場消息", "Market news"),
    "manual": ("市場消息", "Market news"),
}
_SECTION_ORDER: list[tuple[str, str]] = [
    ("重大頭條", "Major headlines"),
    ("市場消息", "Market news"),
]


def _resolved_section_labels(meta: dict) -> tuple[str, str]:
    sz = (meta.get("section_zh") or "").strip()
    se = (meta.get("section_en") or "").strip()
    if sz and se:
        return (sz, se)
    did = (meta.get("domain_id") or "").strip()
    return _SECTION_FALLBACK.get(did, ("市場消息", "Market news"))


def _section_sort_key(key: tuple[str, str]) -> tuple[int, str]:
    try:
        idx = _SECTION_ORDER.index(key)
    except ValueError:
        idx = len(_SECTION_ORDER)
    return (idx, key[0])


def _repair_duplicate_bilingual_article(page_html: str, meta: dict) -> str | None:
    """若 .hermers-i18n-zh 與 .hermers-i18n-en 正文相同（舊版升級遺留），改為繁中／英文各一份。"""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(page_html, "html.parser")
    zh = soup.find("div", class_="hermers-i18n-zh")
    en = soup.find("div", class_="hermers-i18n-en")
    if not zh or not en:
        return None

    def norm(tag) -> str:
        return " ".join(tag.get_text().split())

    if norm(zh) != norm(en):
        return None

    inner = "".join(str(c) for c in zh.contents)
    body_block = build_bilingual_body_block_from_fragment(inner)
    pending = 'data-i18n-zh="待審草稿"' in page_html
    return render_article_page(meta, body_block_html=body_block, pending=pending)


def refresh_dist_article_pages() -> None:
    """將早期極簡版文章升級為與首頁相同皮膚，並校正誤標為草稿的已發布眉批／canonical。"""
    root = posts_dir()
    root.mkdir(parents=True, exist_ok=True)
    for path in sorted(root.glob("*.html")):
        meta_path = path.with_suffix(".json")
        if not meta_path.is_file():
            continue
        slug = path.stem
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        text = path.read_text(encoding="utf-8")
        needs_polish = "__CANONICAL_URL__" in text or 'data-i18n-zh="待審草稿"' in text

        if '<article class="prose">' in text:
            repaired = _repair_duplicate_bilingual_article(text, meta)
            if repaired:
                text = repaired
                path.write_text(text, encoding="utf-8")
                needs_polish = True

        if '<article class="prose">' not in text:
            inner = legacy_minimal_article_inner_body(text)
            if inner is None:
                continue
            body_block = build_bilingual_body_block_from_fragment(inner)
            text = render_article_page(meta, body_block_html=body_block, pending=False)
            path.write_text(text, encoding="utf-8")
            needs_polish = True

        if needs_polish:
            polish_published_post(path, slug=slug)


def rebuild_index() -> None:
    refresh_dist_article_pages()
    posts_dir().mkdir(parents=True, exist_ok=True)
    entries: list[dict] = []
    for path in sorted(posts_dir().glob("*.html"), reverse=True):
        meta_path = path.with_suffix(".json")
        title = path.stem
        published = ""
        domain = ""
        meta: dict = {}
        title_en_meta: str | None = None
        if meta_path.is_file():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            title = meta.get("title") or title
            published = meta.get("approved_at") or ""
            domain = meta.get("domain_name") or ""
            te = meta.get("title_en")
            if isinstance(te, str) and te.strip():
                title_en_meta = te.strip()
        sec_zh, sec_en = _resolved_section_labels(meta)
        entries.append(
            {
                "href": f"posts/{path.name}",
                "title": title,
                "title_en": title_en_meta,
                "published": published,
                "domain": domain,
                "section_zh": sec_zh,
                "section_en": sec_en,
            }
        )

    pending_count = len(list(pending_dir().glob("*/meta.json"))) if pending_dir().is_dir() else 0

    def _entry_li_html(e: dict) -> str:
        date = e["published"][:10] if e["published"] else ""
        tag = html.escape(e["domain"]) if e["domain"] else ""
        sep = " · " if tag and date else ""
        meta_line = f"{tag}{sep}{html.escape(date)}".strip()
        meta_block = (
            f'<span class="meta">{meta_line}</span>\n'
            if meta_line
            else '<span class="meta">—</span>\n'
        )
        tz, te = bilingual_headings_plain(
            e["title"], title_en_hint=e.get("title_en")
        )
        title_zh_esc = html.escape(tz)
        title_en_esc = html.escape(te)
        return (
            f'<li><a href="{html.escape(e["href"])}">'
            f'<span class="hermers-i18n-zh">{title_zh_esc}</span>'
            f'<span class="hermers-i18n-en">{title_en_esc}</span></a>{meta_block}</li>\n'
        )

    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for e in entries:
        grouped[(e["section_zh"], e["section_en"])].append(e)

    section_blocks: list[str] = []
    for sec_key in sorted(grouped.keys(), key=_section_sort_key):
        rows = grouped[sec_key]
        if not rows:
            continue
        sz, se = sec_key
        zh_attr = html.escape(sz, quote=True)
        en_attr = html.escape(se, quote=True)
        lis = "".join(_entry_li_html(row) for row in rows)
        section_blocks.append(
            f'    <section class="category-block">\n'
            f'      <h2 class="category-title"><span data-i18n-zh="{zh_attr}" '
            f'data-i18n-en="{en_attr}"></span></h2>\n'
            f'      <ul class="post-list">\n{lis}      </ul>\n'
            f"    </section>\n"
        )

    list_inner = "".join(section_blocks)

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
    og_title = "台股新聞與行情快訊 | Taiwan Stock News & Market Highlights"
    idx_title_zh = "台股新聞與行情快訊"
    idx_title_en = "Taiwan Stock News & Market Highlights"
    idx_title_zh_attr = html.escape(idx_title_zh, quote=True)
    idx_title_en_attr = html.escape(idx_title_en, quote=True)
    desc_zh = "台股與集中市場相關新聞剪報。"
    desc_en = "Taiwan stock-market news clippings."
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
    list_block = empty_msg if not entries else list_inner
    content = f"""<!DOCTYPE html>
<html lang="zh-Hant" data-hermers-title-zh="{idx_title_zh_attr}" data-hermers-title-en="{idx_title_en_attr}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="color-scheme" content="light" />
{head_seo}  <title>{html.escape(idx_title_zh)}</title>
  <style>{css}
  </style>
</head>
<body>
  {lang_switcher_html()}
  <main>
    <header class="masthead">
      <h1><span data-i18n-zh="台股新聞與行情快訊" data-i18n-en="Taiwan Stock News & Market Highlights"></span></h1>
      <p class="sub"><span data-i18n-zh="台股與集中市場相關新聞剪報。"
        data-i18n-en="Taiwan stock-market news clippings."></span></p>
      <div class="stats">
        <span class="pill"><span data-i18n-zh="待審" data-i18n-en="Pending"></span>
          <strong>{pending_count}</strong>
          <span data-i18n-zh="則" data-i18n-en="items"></span></span>
        <span class="pill"><span data-i18n-zh="已發布" data-i18n-en="Published"></span>
          <strong>{len(entries)}</strong>
          <span data-i18n-zh="則" data-i18n-en="items"></span></span>
      </div>
    </header>
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
