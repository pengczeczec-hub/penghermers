from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermers.discover import FeedItem
from hermers.fetch import ArticleExtract
from hermers.i18n_ui import i18n_runtime_script, lang_switcher_css, lang_switcher_html, seo_block
from hermers.static_skin import css_article_specific, css_base, css_shell
from hermers.translate_body import zh_paragraphs_from_extract, zh_title_from_extract


def _clip_paragraphs_for_digest(paragraphs: list[str], *, total_max: int = 9000) -> list[str]:
    out: list[str] = []
    n = 0
    for raw in paragraphs:
        piece = raw.strip()
        if not piece:
            continue
        if n + len(piece) > total_max:
            rest = total_max - n
            if rest > 80:
                out.append(piece[:rest])
            break
        out.append(piece)
        n += len(piece) + 2
    return out


def _is_latin_primary(text: str) -> bool:
    if not text.strip():
        return True
    cjk = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    return cjk < max(12, len(text) // 40)


def _truncate_display(s: str, max_chars: int) -> str:
    s = s.strip()
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 1].rstrip() + "…"


def _fallback_bullet_lists(paras: list[str], merged: str) -> tuple[list[str], list[str]]:
    """無 LLM 時：各至多 5 條短句（截斷），避免刊登長篇原文。"""
    chunks = re.split(r"(?<=[。．!?])\s+|(?<=\.)\s+", merged)
    candidates = [c.strip() for c in chunks if len(c.strip()) >= 18]
    if len(candidates) < 3 and paras:
        candidates.extend([p.strip() for p in paras if len(p.strip()) >= 18])
    if len(candidates) < 3 and merged.strip():
        text = merged.strip()
        step = max(72, min(140, len(text) // 4 or 72))
        slice_pts = list(range(0, len(text), step))[:5]
        pseudo = [text[i : i + step].strip() for i in slice_pts]
        candidates.extend([p for p in pseudo if len(p) >= 20])
    seen: set[str] = set()
    deduped: list[str] = []
    for c in candidates:
        key = c[:48]
        if key in seen:
            continue
        seen.add(key)
        deduped.append(c)
        if len(deduped) >= 8:
            break
    candidates = deduped

    latin = _is_latin_primary(merged)
    if latin:
        bullets_en = [_truncate_display(c, 130) for c in candidates[:5]]
        if len(bullets_en) < 3 and merged.strip():
            bullets_en.append(_truncate_display(merged, 120))
            bullets_en.append(_truncate_display(merged[max(len(merged) // 3, 1) :], 120))
        bullets_en = bullets_en[:5]
        zh_from_en = zh_paragraphs_from_extract(bullets_en)
        bullets_zh = [_truncate_display(z, 130) for z in zh_from_en[: len(bullets_en)]]
    else:
        bullets_zh = [_truncate_display(c, 130) for c in candidates[:5]]
        if len(bullets_zh) < 3 and merged.strip():
            bullets_zh.append(_truncate_display(merged, 120))
            bullets_zh.append(_truncate_display(merged[max(len(merged) // 3, 1) :], 120))
        bullets_zh = bullets_zh[:5]
        from hermers.translate_llm import llm_batch_zh_to_en, llm_translate_available

        if llm_translate_available():
            be = llm_batch_zh_to_en(bullets_zh)
            if be is not None and len(be) == len(bullets_zh):
                bullets_en = [_truncate_display(x, 160) for x in be]
            else:
                bullets_en = list(bullets_zh)
        else:
            bullets_en = list(bullets_zh)
    n = min(len(bullets_zh), len(bullets_en), 5)
    return bullets_zh[:n], bullets_en[:n]


def _fallback_clipping_digest(item: FeedItem, extract: ArticleExtract) -> dict[str, Any]:
    rss = (item.title or "").strip()
    page = (extract.title or "").strip()
    headline_src = page or rss

    paras = _clip_paragraphs_for_digest(extract.paragraphs)
    merged = "\n".join(paras).strip()
    bullets_zh, bullets_en = _fallback_bullet_lists(paras, merged or page or rss)

    if any("\u4e00" <= c <= "\u9fff" for c in headline_src):
        title_zh = headline_src[:120]
        from hermers.translate_llm import llm_translate_available, llm_zh_to_en_title

        te = llm_zh_to_en_title(title_zh) if llm_translate_available() else None
        title_en = te if te else title_zh
    else:
        title_zh = zh_title_from_extract(headline_src) or rss or headline_src
        title_en = headline_src[:200] if headline_src else title_zh

    return {
        "title_zh": title_zh,
        "title_en": title_en,
        "bullets_zh": bullets_zh,
        "bullets_en": bullets_en,
        "short_zh": "",
        "short_en": "",
    }


def _compute_clipping_digest(item: FeedItem, extract: ArticleExtract) -> dict[str, Any]:
    from hermers.translate_llm import llm_bilingual_clipping_digest

    digest = llm_bilingual_clipping_digest(
        rss_title=item.title or "",
        page_title=extract.title or "",
        paragraphs=list(extract.paragraphs),
    )
    if digest:
        return digest
    return _fallback_clipping_digest(item, extract)


def _digest_body_html(digest: dict[str, Any]) -> str:
    kicker = (
        '<p class="digest-kicker"><span data-i18n-zh="以下為依公開來源素材整理之重點（約三～五點），非原文全文轉載。" '
        'data-i18n-en="Key points summarized from public sources (about 3–5 bullets)—not a full reproduction of the original article."></span></p>'
    )
    ul_zh = "".join(f"<li>{html.escape(x)}</li>" for x in digest["bullets_zh"])
    ul_en = "".join(f"<li>{html.escape(x)}</li>" for x in digest["bullets_en"])
    short_zh = ""
    short_en = ""
    if digest.get("short_zh"):
        short_zh = f'<p class="digest-short">{html.escape(digest["short_zh"])}</p>'
    if digest.get("short_en"):
        short_en = f'<p class="digest-short">{html.escape(digest["short_en"])}</p>'
    return f"""      <div class="hermers-i18n-zh">{kicker}<ul class="digest-bullets">{ul_zh}</ul>{short_zh}</div>
      <div class="hermers-i18n-en">{kicker}<ul class="digest-bullets">{ul_en}</ul>{short_en}</div>
"""


def write_pending(
    folder: Path,
    *,
    item: FeedItem,
    extract: ArticleExtract,
    draft_id: str,
) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    digest = _compute_clipping_digest(item, extract)
    summary = "\n".join(f"- {x}" for x in digest["bullets_zh"][:5])
    meta = {
        "id": draft_id,
        "status": "pending",
        "domain_id": item.domain_id,
        "domain_name": item.domain_name,
        "section_zh": item.section_zh,
        "section_en": item.section_en,
        "title": digest["title_zh"],
        "title_en": digest["title_en"],
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
        _draft_html(meta, digest), encoding="utf-8"
    )


def _cursor_task(meta: dict, summary: str) -> str:
    return f"""# Cursor 潤稿任務（可選）

待審草稿：`{meta["id"]}`
原文：{meta["url"]}

請在通過審核前，視需要調整 `draft.html`：本站僅刊登「改寫標題 + 雙語重點條列」（非全文）；請維持摘要性質並保留來源連結。

## 自動整理之重點（繁中）

{summary[:2000]}
"""


def paragraph_chunks_to_ps(parts: list[str]) -> str:
    chunks: list[str] = []
    for raw in parts:
        for piece in (s.strip() for s in raw.split("\n\n")):
            if piece:
                chunks.append(f"<p>{html.escape(piece)}</p>")
    return "".join(chunks)


def bilingual_headings_plain(
    title_raw: str, *, title_en_hint: str | None = None
) -> tuple[str, str]:
    """回傳 (title_zh_plain, title_en_plain)。英文來源：繁中標題／英文原文；中文來源：原文／英文標題（可帶入已改寫的 title_en_hint）。"""
    raw = title_raw.strip()
    hint = (title_en_hint or "").strip()
    if any("\u4e00" <= c <= "\u9fff" for c in raw):
        zh_plain = raw
        if hint:
            en_plain = hint
        else:
            en_plain = raw
            from hermers.translate_llm import llm_translate_available, llm_zh_to_en_title

            if llm_translate_available():
                e = llm_zh_to_en_title(zh_plain[:500])
                if e and e != zh_plain:
                    en_plain = e
        return zh_plain, en_plain
    zh_plain = zh_title_from_extract(raw) or raw
    en_plain = hint if hint else raw
    return zh_plain, en_plain


def build_bilingual_body_block_from_fragment(inner_html: str) -> str:
    """由 legacy 正文 HTML 產生中英各一份 body block（含 div.hermers-i18n-*）。"""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(inner_html, "html.parser")
    paras: list[str] = []
    for p in soup.find_all("p"):
        t = " ".join(p.stripped_strings)
        if t:
            paras.append(t)
    if not paras:
        plain = soup.get_text("\n", strip=True)
        paras = [x.strip() for x in plain.split("\n\n") if x.strip()]
    if not paras:
        inner_esc = inner_html.strip()
        return f"""      <div class="hermers-i18n-zh">{inner_esc}</div>
      <div class="hermers-i18n-en">{inner_esc}</div>
"""
    joined = "\n".join(paras)
    cjk = sum(1 for c in joined if "\u4e00" <= c <= "\u9fff")
    latin_primary = cjk < max(12, max(8, len(joined) // 50))
    if latin_primary:
        body_zh = paragraph_chunks_to_ps(zh_paragraphs_from_extract(paras))
        body_en = paragraph_chunks_to_ps(list(paras))
    else:
        from hermers.translate_llm import llm_batch_zh_to_en, llm_translate_available

        body_zh = paragraph_chunks_to_ps(list(paras))
        filled = llm_batch_zh_to_en(paras) if llm_translate_available() else None
        if filled is not None and len(filled) == len(paras):
            body_en = paragraph_chunks_to_ps(filled)
        else:
            body_en = body_zh
    return f"""      <div class="hermers-i18n-zh">{body_zh}</div>
      <div class="hermers-i18n-en">{body_en}</div>
"""


def render_article_page(
    meta: dict,
    *,
    body_block_html: str,
    pending: bool,
    title_raw: str | None = None,
    title_en_hint: str | None = None,
) -> str:
    """共用單頁版面：RSS 草稿、手動重建或升級 legacy dist 文章皆可呼叫。"""
    t_raw = title_raw if title_raw is not None else str(meta["title"])
    hint = title_en_hint
    if hint is None:
        te_meta = meta.get("title_en")
        hint = te_meta if isinstance(te_meta, str) and te_meta.strip() else None
    tz_plain, te_plain = bilingual_headings_plain(
        t_raw, title_en_hint=hint if hint else None
    )
    title_zh_esc = html.escape(tz_plain)
    title_en_esc = html.escape(te_plain)
    title_zh_attr = html.escape(tz_plain, quote=True)
    title_en_attr = html.escape(te_plain, quote=True)
    url = html.escape(meta["url"])
    domain = html.escape(meta["domain_name"])
    if pending:
        desc_zh = f"「{t_raw}」剪報草稿（待審），來源連結於文內。"
        desc_en = f'Clipping draft (pending): "{t_raw}". Source link inside.'
        eyebrow = f'{domain} · <span data-i18n-zh="待審草稿" data-i18n-en="Pending draft"></span>'
        foot = (
            '<span data-i18n-zh="內容為改寫標題與重點整理（非原文全文）；通過審核後會進入 dist/ 並可部署上線。"'
            ' data-i18n-en="Rewritten headline and summarized key points (not the full original text); after approval this goes to dist/ for deploy."></span>'
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
    title_tab = title_zh_esc
    return f"""<!DOCTYPE html>
<html lang="zh-Hant" data-hermers-title-zh="{title_zh_attr}" data-hermers-title-en="{title_en_attr}">
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


def _draft_html(meta: dict, digest: dict[str, Any]) -> str:
    title_raw = meta["title"]
    title_en_hint = meta.get("title_en") if isinstance(meta.get("title_en"), str) else None
    if digest["bullets_zh"]:
        body = _digest_body_html(digest)
    else:
        empty_inner = (
            "<p><em><span data-i18n-zh=\"（素材不足，請依上方原文連結補寫重點後再送審。）\""
            ' data-i18n-en="(Insufficient extracted material—please add key points from the source link before review.)">'
            "</span></em></p>"
        )
        body = f"""      <div class="hermers-i18n-zh">{empty_inner}</div>
      <div class="hermers-i18n-en">{empty_inner}</div>
"""
    return render_article_page(
        meta,
        body_block_html=body,
        pending=True,
        title_raw=title_raw,
        title_en_hint=title_en_hint,
    )


def legacy_minimal_article_inner_body(page_html: str) -> str | None:
    """從早期 system-ui 版型擷取 <hr /> 之間正文（連續段落 HTML）。"""
    parts = page_html.split("<hr />")
    if len(parts) < 3:
        return None
    inner = parts[1].strip()
    return inner if inner else None
