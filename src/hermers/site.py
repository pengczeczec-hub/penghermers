from __future__ import annotations

import html
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from hermers.draft import (
    bilingual_headings_plain,
    build_bilingual_body_block_from_fragment,
    legacy_minimal_article_inner_body,
    render_article_page,
    _digest_body_html,
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
from hermers.home_index import (
    HOME_ARCHIVE_DAYS,
    enrich_entry,
    entry_calendar_date,
    in_archive_window,
    pick_weekly_top5,
    week_start,
)
from hermers.paths import dist_dir, pending_dir, posts_dir
from hermers.segment import analyze_site_segment, dual_tw_us_for_home, infer_site_segment
from hermers.static_skin import css_base, css_index_specific, css_review_specific, css_shell

# 首頁分類順序（對應 domains.yaml 的 section_*）；舊稿無欄位時依 domain_id 回退。
_SECTION_FALLBACK: dict[str, tuple[str, str]] = {
    "tw_market_extra": ("重大頭條", "Major headlines"),
    "tw_stock": ("市場消息", "Market news"),
    "us_stock": ("美股消息", "U.S. & global equities"),
    "crypto_news": ("加密貨幣", "Cryptocurrencies"),
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


def _index_market_tabs_html() -> str:
    """可擴充：另增標籤時加 role=tab + data-hermers-market 並更新腳本 allowed。"""
    return """<nav class="market-tabs" role="tablist" aria-label="市場區塊">
  <button type="button" role="tab" data-hermers-market="all" aria-selected="true"><span data-i18n-zh="全部" data-i18n-en="All"></span></button>
  <button type="button" role="tab" data-hermers-market="tw" aria-selected="false"><span data-i18n-zh="台股" data-i18n-en="TW stocks"></span></button>
  <button type="button" role="tab" data-hermers-market="us" aria-selected="false"><span data-i18n-zh="美股" data-i18n-en="US stocks"></span></button>
  <button type="button" role="tab" data-hermers-market="crypto" aria-selected="false"><span data-i18n-zh="加密貨幣" data-i18n-en="Crypto"></span></button>
</nav>"""


def _index_date_filter_script(
    *,
    week_start_iso: str,
    today_iso: str,
    dates_available: list[str],
) -> str:
    dates_json = json.dumps(dates_available, ensure_ascii=False)
    return f"""<script>
(function () {{
  var WEEK_START = {json.dumps(week_start_iso)};
  var TODAY = {json.dumps(today_iso)};
  var DATES = {dates_json};

  function applyDateFilter(mode, dayIso) {{
    var weekMode = mode === "week";
    document.querySelectorAll(".post-list li[data-hermers-date]").forEach(function (li) {{
      var d = li.getAttribute("data-hermers-date") || "";
      var inWeek = li.getAttribute("data-hermers-in-week") === "1";
      var show = weekMode ? inWeek : (dayIso && d === dayIso);
      li.hidden = !show;
    }});
    document.querySelectorAll(".spotlight-card[data-hermers-date]").forEach(function (card) {{
      var d = card.getAttribute("data-hermers-date") || "";
      var inWeek = card.getAttribute("data-hermers-in-week") === "1";
      var show = weekMode ? inWeek : (dayIso && d === dayIso);
      card.hidden = !show;
    }});
    var spotlight = document.getElementById("hermers-weekly-spotlight");
    if (spotlight) {{
      var anyCard = false;
      spotlight.querySelectorAll(".spotlight-card").forEach(function (c) {{
        if (!c.hidden) anyCard = true;
      }});
      spotlight.hidden = !anyCard;
    }}
    document.querySelectorAll(".list-wrap .category-block").forEach(function (block) {{
      var lis = block.querySelectorAll("li[data-hermers-date]");
      var showBlock = false;
      lis.forEach(function (li) {{ if (!li.hidden) showBlock = true; }});
      block.hidden = !showBlock;
    }});
    var emptyDay = document.getElementById("hermers-day-empty");
    if (emptyDay) {{
      var hasVisible = document.querySelector(".post-list li[data-hermers-date]:not([hidden])");
      emptyDay.hidden = weekMode || !dayIso || !!hasVisible;
    }}
    if (window.hermersApplyMarketTab) window.hermersApplyMarketTab(
      (function () {{
        try {{ return sessionStorage.getItem("hermers_market_tab") || "all"; }} catch (e) {{ return "all"; }}
      }})()
    );
  }}

  function setModeButtons(weekOn) {{
    document.querySelectorAll("[data-hermers-date-mode]").forEach(function (btn) {{
      var m = btn.getAttribute("data-hermers-date-mode");
      btn.setAttribute("aria-pressed", (weekOn && m === "week") || (!weekOn && m === "day") ? "true" : "false");
    }});
  }}

  document.addEventListener("DOMContentLoaded", function () {{
    var input = document.getElementById("hermers-date-pick");
    var minD = DATES.length ? DATES[DATES.length - 1] : WEEK_START;
    var maxD = DATES.length ? DATES[0] : TODAY;
    if (input) {{
      input.min = minD;
      input.max = maxD;
      input.value = TODAY;
    }}
    applyDateFilter("week", null);
    setModeButtons(true);

    document.querySelectorAll("[data-hermers-date-mode]").forEach(function (btn) {{
      btn.addEventListener("click", function () {{
        var mode = btn.getAttribute("data-hermers-date-mode");
        if (mode === "week") {{
          if (input) input.value = TODAY;
          applyDateFilter("week", null);
          setModeButtons(true);
        }}
      }});
    }});

    if (input) {{
      input.addEventListener("change", function () {{
        var v = input.value;
        if (!v) return;
        applyDateFilter("day", v);
        setModeButtons(false);
      }});
    }}
  }});
}})();
</script>"""


def _index_date_toolbar_html(*, today_iso: str) -> str:
    return f"""<motion class="date-toolbar" aria-label="日期瀏覽">
  <label for="hermers-date-pick"><span data-i18n-zh="選擇日期" data-i18n-en="Pick a date"></span></label>
  <input type="date" id="hermers-date-pick" name="hermers-date" value="{html.escape(today_iso)}" />
  <button type="button" class="date-mode-btn" data-hermers-date-mode="week" aria-pressed="true">
    <span data-i18n-zh="本週精選" data-i18n-en="This week"></span>
  </button>
</motion>""".replace("<motion", "<div", 1).replace("</motion>", "</div>", 1)


def _spotlight_card_html(rank: int, e: dict) -> str:
    date_iso = html.escape(e.get("post_date_iso") or "")
    in_week = "1" if e.get("in_week") else "0"
    tz, te = bilingual_headings_plain(e["title"], title_en_hint=e.get("title_en"))
    tag = html.escape(e["domain"]) if e.get("domain") else ""
    date_disp = html.escape(e.get("post_date_iso") or "")
    meta_line = f"{tag} · {date_disp}" if tag and date_disp else (tag or date_disp or "—")
    return (
        f'<li class="spotlight-card" data-hermers-date="{date_iso}" '
        f'data-hermers-in-week="{in_week}">'
        f'<span class="spotlight-rank" aria-hidden="true">{rank}</span>'
        f'<div><a href="{html.escape(e["href"])}">'
        f'<span class="hermers-i18n-zh">{html.escape(tz)}</span>'
        f'<span class="hermers-i18n-en">{html.escape(te)}</span></a>'
        f'<span class="spotlight-meta">{meta_line}</span></div></li>\n'
    )


def _weekly_spotlight_html(top5: list[dict]) -> str:
    if not top5:
        return ""
    cards = "".join(_spotlight_card_html(i + 1, e) for i, e in enumerate(top5))
    return (
        '<section class="weekly-spotlight" id="hermers-weekly-spotlight">\n'
        '  <h2><span data-i18n-zh="本週焦點精選（Weekly Top 5）" '
        'data-i18n-en="Weekly Top 5 Highlights"></span></h2>\n'
        f'  <ol class="spotlight-grid">\n{cards}  </ol>\n'
        "</section>\n"
    )


def _index_segment_tabs_script() -> str:
    return """<script>
(function () {
  function applyMarketTab(tab) {
    var seg = tab || "all";
    var allowed = { all: 1, tw: 1, us: 1, crypto: 1 };
    if (!allowed[seg]) seg = "all";
    try { sessionStorage.setItem("hermers_market_tab", seg); } catch (e) {}
    document.querySelectorAll(".market-tabs [data-hermers-market]").forEach(function (btn) {
      var id = btn.getAttribute("data-hermers-market");
      btn.setAttribute("aria-selected", id === seg ? "true" : "false");
    });
    document.querySelectorAll(".list-wrap .category-block").forEach(function (block) {
      var lis = block.querySelectorAll("li[data-hermers-segment]");
      var showBlock = false;
      lis.forEach(function (li) {
        var lseg = li.getAttribute("data-hermers-segment") || "other";
        var dual = li.getAttribute("data-hermers-tw-us-cross") === "1";
        var show = seg === "all" || lseg === seg ||
          (dual && (seg === "tw" || seg === "us"));
        li.hidden = !show;
        if (show) showBlock = true;
      });
      block.hidden = !showBlock;
    });
    var emptyNote = document.getElementById("hermers-market-empty");
    if (!emptyNote) return;
    var blocks = document.querySelectorAll(".list-wrap .category-block");
    var any = false;
    blocks.forEach(function (b) { if (!b.hidden) any = true; });
    emptyNote.hidden = any;
  }

  document.addEventListener("click", function (e) {
    var t = e.target;
    if (!t || !t.closest) return;
    var btn = t.closest("[data-hermers-market]");
    if (!btn || !btn.classList) return;
    if (!btn.closest(".market-tabs")) return;
    e.preventDefault();
    applyMarketTab(btn.getAttribute("data-hermers-market"));
  });

  window.hermersApplyMarketTab = applyMarketTab;
  document.addEventListener("DOMContentLoaded", function () {
    var init = "all";
    try { init = sessionStorage.getItem("hermers_market_tab") || "all"; } catch (e2) {}
    applyMarketTab(init);
  });
})();
</script>"""


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


def _repair_digest_en_still_zh(page_html: str, meta: dict) -> str | None:
    """條列剪報：英文欄仍為繁中時，依中文條目重翻英文並重組 body。"""
    from bs4 import BeautifulSoup

    from hermers.translate_body import (
        en_paragraphs_from_zh_sequence,
        snippet_looks_mostly_english,
        translate_zh_to_en,
    )
    from hermers.translate_llm import llm_batch_zh_to_en, llm_translate_available

    soup = BeautifulSoup(page_html, "html.parser")
    zh = soup.find("div", class_="hermers-i18n-zh")
    en = soup.find("div", class_="hermers-i18n-en")
    if not zh or not en or not zh.select_one("ul.digest-bullets"):
        return None
    bullets_zh = [li.get_text(" ", strip=True) for li in zh.select("ul.digest-bullets li")]
    bullets_en_old = [li.get_text(" ", strip=True) for li in en.select("ul.digest-bullets li")]
    if len(bullets_zh) < 3 or len(bullets_en_old) != len(bullets_zh):
        return None
    if all(snippet_looks_mostly_english(x) for x in bullets_en_old):
        return None

    be: list[str] | None = None
    if llm_translate_available():
        cand = llm_batch_zh_to_en(bullets_zh)
        if cand is not None and len(cand) == len(bullets_zh):
            if all(snippet_looks_mostly_english(x) for x in cand):
                be = cand
    if be is None:
        be = en_paragraphs_from_zh_sequence(bullets_zh)
    if be is None:
        return None

    short_zh, short_en = "", ""
    pz = zh.select_one("p.digest-short")
    pe = en.select_one("p.digest-short")
    if pz:
        short_zh = pz.get_text(strip=True)
    if pe:
        short_en = pe.get_text(strip=True)
    if short_zh and short_en and not snippet_looks_mostly_english(short_en):
        st = translate_zh_to_en(short_zh)
        if st and snippet_looks_mostly_english(st):
            short_en = st.strip()[:220]
            if len(short_en) > 150:
                short_en = short_en[:149].rstrip() + "…"

    digest = {
        "bullets_zh": bullets_zh,
        "bullets_en": be,
        "short_zh": short_zh,
        "short_en": short_en,
    }
    body_block = _digest_body_html(digest)
    pending = 'data-i18n-zh="待審草稿"' in page_html
    return render_article_page(meta, body_block_html=body_block, pending=pending)


def _repair_chinese_english_column(page_html: str, meta: dict) -> str | None:
    """長段剪報：英文欄仍像繁中時，以中文正文重產英文段落。"""
    if "digest-bullets" in page_html:
        return _repair_digest_en_still_zh(page_html, meta)

    from bs4 import BeautifulSoup

    from hermers.translate_body import passage_looks_mostly_english

    soup = BeautifulSoup(page_html, "html.parser")
    zh = soup.find("div", class_="hermers-i18n-zh")
    en = soup.find("div", class_="hermers-i18n-en")
    if not zh or not en:
        return None
    if passage_looks_mostly_english(en.get_text()):
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

        if '<article class="prose">' in text:
            repaired_en = _repair_chinese_english_column(text, meta)
            if repaired_en:
                text = repaired_en
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
        analysis = analyze_site_segment(meta, slug=path.stem)
        row = {
            "href": f"posts/{path.name}",
            "title": title,
            "title_en": title_en_meta,
            "published": published,
            "domain": domain,
            "section_zh": sec_zh,
            "section_en": sec_en,
            "segment": infer_site_segment(meta, slug=path.stem),
            "cross_tw_us": dual_tw_us_for_home(analysis),
        }
        row = enrich_entry(row, meta, path.stem)
        if in_archive_window(row.get("post_date")):
            entries.append(row)

    for ri, row in enumerate(entries):
        row["global_rank"] = ri + 1

    today = datetime.now(timezone.utc).date()
    week_start_iso = week_start(today).isoformat()
    today_iso = today.isoformat()
    dates_available = sorted(
        {e["post_date_iso"] for e in entries if e.get("post_date_iso")},
        reverse=True,
    )
    top5 = pick_weekly_top5(entries, today=today)
    spotlight_block = _weekly_spotlight_html(top5)
    date_toolbar = _index_date_toolbar_html(today_iso=today_iso)

    def _entry_li_html(e: dict) -> str:
        date = e.get("post_date_iso") or (e["published"][:10] if e["published"] else "")
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
        seg = e.get("segment") or "other"
        if seg not in ("tw", "us", "crypto", "other"):
            seg = "other"
        seg_esc = html.escape(seg)
        cross_attr = ""
        if e.get("cross_tw_us") and int(e.get("global_rank") or 999) <= 10:
            cross_attr = ' data-hermers-tw-us-cross="1"'
        date_iso = html.escape(e.get("post_date_iso") or "")
        in_week = "1" if e.get("in_week") else "0"
        return (
            f'<li data-hermers-segment="{seg_esc}" data-hermers-date="{date_iso}" '
            f'data-hermers-in-week="{in_week}"{cross_attr}><a href="{html.escape(e["href"])}">'
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
    og_title = "Hermers 市場剪報｜Hermers Market Digest"
    idx_title_zh = "Hermers 市場剪報"
    idx_title_en = "Hermers Market Digest"
    idx_title_zh_attr = html.escape(idx_title_zh, quote=True)
    idx_title_en_attr = html.escape(idx_title_en, quote=True)
    desc_zh = "台股、美股、加密貨幣等市場剪報提要（首頁標籤可擴充）。跨台／美題材僅於全站排序前十名內雙標籤露出。"
    desc_en = (
        "Taiwan, U.S., and crypto market digests—tabs expand over time. "
        "Dual TW/US labeling applies only to posts in the site-wide top ten."
    )
    head_seo = seo_block(
        canonical_url=index_canonical,
        og_title=og_title,
        description_zh=desc_zh,
        description_en=desc_en,
    )
    empty_msg = (
        '<p class="empty"><span data-i18n-zh="尚無已發布文章。" '
        'data-i18n-en="No published stories yet."></span></p>'
    )
    market_empty_hint = """<p id="hermers-market-empty" class="empty" hidden>
      <span data-i18n-zh="目前此市場標籤下沒有文章，請改選「全部」或試其他區塊。"
        data-i18n-en="No posts under this market tab. Switch to All or try another beat."></span>
    </p>"""
    day_empty_hint = """<p id="hermers-day-empty" class="empty" hidden>
      <span data-i18n-zh="此日期沒有剪報，請選其他日期或返回本週。"
        data-i18n-en="No clippings on this date. Pick another day or return to this week."></span>
    </p>"""
    if entries:
        list_block = market_empty_hint + day_empty_hint + list_inner
    else:
        list_block = empty_msg
    tabs_strip = _index_market_tabs_html() if entries else ""
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
      <h1><span data-i18n-zh="Hermers 市場剪報" data-i18n-en="Hermers Market Digest"></span></h1>
      <p class="sub"><span data-i18n-zh="台股、美股、加密貨幣新聞剪報；預設顯示近 7 日，可用日期選擇器瀏覽歷史。"
        data-i18n-en="Taiwan, U.S., and crypto digests—last 7 days by default; use the date picker for archives."></span></p>
      {date_toolbar}
      {tabs_strip}
    </header>
    {spotlight_block}
    <div class="list-wrap">
      {list_block}
    </div>
    <footer class="time"><span data-i18n-zh="更新時間（UTC）·" data-i18n-en="Last update (UTC)·"></span>
      {html.escape(datetime.now(timezone.utc).isoformat(timespec="seconds"))}</footer>
  </main>
{i18n_runtime_script()}
{_index_date_filter_script(week_start_iso=week_start_iso, today_iso=today_iso, dates_available=dates_available)}
{_index_segment_tabs_script()}
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
