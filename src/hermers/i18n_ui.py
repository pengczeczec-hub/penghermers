"""剪報站共用：中英介面切換（localStorage + ?lang=）與雙語 SEO 標頭輔助。"""

from __future__ import annotations

import html
import os
import re
from pathlib import Path


def public_base_url() -> str:
    from hermers.env_load import load_dotenv

    load_dotenv()
    return os.environ.get("SITE_PUBLIC_URL", "").strip().rstrip("/")


def lang_switcher_css() -> str:
    return """
  .lang-switch {
    position: fixed;
    top: 0.75rem;
    right: 0.75rem;
    z-index: 50;
    display: flex;
    gap: 0.35rem;
    background: var(--surface-elev, #fff);
    border: 1px solid var(--border, #e7e5e0);
    border-radius: 999px;
    padding: 0.2rem;
    box-shadow: var(--shadow, 0 2px 8px rgba(0,0,0,0.08));
  }
  .lang-switch .lang-btn {
    cursor: pointer;
    border: none;
    background: transparent;
    color: var(--muted, #78716c);
    font: inherit;
    font-size: 0.78rem;
    font-weight: 600;
    padding: 0.35rem 0.65rem;
    border-radius: 999px;
    line-height: 1;
  }
  .lang-switch .lang-btn:hover { color: var(--accent-hover, #0d5c56); }
  .lang-switch .lang-btn[aria-pressed="true"] {
    background: var(--accent-soft, rgba(15, 118, 110, 0.12));
    color: var(--ink, #1c1917);
  }
  html[lang="en"] .hermers-i18n-zh { display: none !important; }
  html[lang="zh-Hant"] .hermers-i18n-en { display: none !important; }
"""


def lang_switcher_html(*, compact: bool = False) -> str:
    aria = ' aria-label="介面語言 / Language"'
    if compact:
        return f"""<div class="lang-switch" role="group"{aria}>
  <button type="button" class="lang-btn" data-set-lang="zh-Hant" aria-pressed="true">中</button>
  <button type="button" class="lang-btn" data-set-lang="en" aria-pressed="false">EN</button>
</div>"""
    return f"""<div class="lang-switch" role="group"{aria}>
  <button type="button" class="lang-btn" data-set-lang="zh-Hant" aria-pressed="true">繁中</button>
  <button type="button" class="lang-btn" data-set-lang="en" aria-pressed="false">English</button>
</div>"""


def i18n_runtime_script() -> str:
    return """<script>
(function () {
  var K = "hermers_lang";
  function norm(q) {
    if (q === "en" || q === "en-US") return "en";
    if (q === "zh" || q === "zh-Hant" || q === "zh-TW" || q === "tw") return "zh-Hant";
    return null;
  }
  var sp = new URLSearchParams(location.search).get("lang");
  var n = norm(sp);
  if (n) localStorage.setItem(K, n);

  function apply() {
    var lang = localStorage.getItem(K) || "zh-Hant"; // en | zh-Hant
    document.documentElement.lang = lang === "en" ? "en" : "zh-Hant";
    var zht = document.documentElement.getAttribute("data-hermers-title-zh");
    var ent = document.documentElement.getAttribute("data-hermers-title-en");
    if (zht !== null && ent !== null && zht !== "" && ent !== "") {
      document.title = lang === "en" ? ent : zht;
    }
    document.querySelectorAll("[data-i18n-zh][data-i18n-en]").forEach(function (el) {
      var zh = el.getAttribute("data-i18n-zh") || "";
      var en = el.getAttribute("data-i18n-en") || "";
      el.textContent = lang === "en" ? en : zh;
    });
    document.querySelectorAll(".lang-switch .lang-btn").forEach(function (btn) {
      var v = btn.getAttribute("data-set-lang");
      var on = (v === "en" && lang === "en") || (v === "zh-Hant" && lang !== "en");
      btn.setAttribute("aria-pressed", on ? "true" : "false");
    });
  }

  window.hermersSetLang = function (l) {
    localStorage.setItem(K, l === "en" ? "en" : "zh-Hant");
    apply();
  };

  document.addEventListener("click", function (e) {
    var t = e.target;
    if (!t || !t.getAttribute) return;
    var v = t.getAttribute("data-set-lang");
    if (v === "en" || v === "zh-Hant") {
      e.preventDefault();
      window.hermersSetLang(v);
    }
  });

  apply();
})();
</script>"""


def seo_block(
    *,
    canonical_url: str,
    og_title: str,
    description_zh: str,
    description_en: str,
    og_type: str = "website",
) -> str:
    """雙語摘要供搜尋摘錄；hreflang 指向同一 canonical（使用者可切語系之同一頁）。"""
    desc_combo = f"{description_zh} {description_en}".strip()
    esc = html.escape
    og_title_e = esc(og_title)
    desc_e = esc(desc_combo)
    url_e = esc(canonical_url) if canonical_url else ""
    lines: list[str] = [
        f'  <meta name="description" content="{desc_e}" />',
        '  <meta property="og:title" content="' + og_title_e + '" />',
        '  <meta property="og:description" content="' + desc_e + '" />',
        '  <meta property="og:type" content="' + esc(og_type) + '" />',
        '  <meta property="og:locale" content="zh_TW" />',
        '  <meta property="og:locale:alternate" content="en_US" />',
    ]
    if url_e:
        lines += [
            f'  <link rel="canonical" href="{url_e}" />',
            f'  <link rel="alternate" hreflang="zh-Hant" href="{url_e}" />',
            f'  <link rel="alternate" hreflang="en" href="{url_e}" />',
            f'  <link rel="alternate" hreflang="x-default" href="{url_e}" />',
            '  <meta property="og:url" content="' + url_e + '" />',
        ]
    return "\n".join(lines) + "\n"


def strip_empty_seo_placeholders(page_html: str) -> str:
    """若未設定 SITE_PUBLIC_URL，移除缺網址的 canonical / og:url / hreflang。"""
    out = page_html
    out = re.sub(r'^\s*<link rel="canonical" href="" />\s*\n', "", out, flags=re.MULTILINE)
    out = re.sub(
        r'^\s*<link rel="alternate" hreflang="(?:zh-Hant|en|x-default)" href="" />\s*\n',
        "",
        out,
        flags=re.MULTILINE,
    )
    out = re.sub(r'^\s*<meta property="og:url" content="" />\s*\n', "", out, flags=re.MULTILINE)
    return out


def polish_published_post(path: Path, *, slug: str) -> None:
    """核准後寫入 dist：替換 canonical 佔位、眉批／頁尾由「草稿」→「已發布」，並在無網址時清掉空 rel/meta。"""
    text = path.read_text(encoding="utf-8")
    base = public_base_url()
    canonical = f"{base}/posts/{slug}.html" if base else ""
    if "__CANONICAL_URL__" in text:
        text = text.replace("__CANONICAL_URL__", html.escape(canonical))
    text = text.replace(
        'data-i18n-zh="待審草稿" data-i18n-en="Pending draft"',
        'data-i18n-zh="已發布" data-i18n-en="Published"',
    )
    text = text.replace(
        'data-i18n-zh="自動擷取摘要；通過審核後會進入 dist/ 並可部署上線。"',
        'data-i18n-zh="已審核發布於 Hermers 剪報站；可追溯原文連結。"',
    )
    text = text.replace(
        'data-i18n-en="Auto-extracted summary; after approval this goes to dist/ for deploy."',
        'data-i18n-en="Published on Hermers Digest; original source linked above."',
    )
    text = strip_empty_seo_placeholders(text)
    path.write_text(text, encoding="utf-8")
