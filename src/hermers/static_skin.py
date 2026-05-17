"""共用內嵌樣式：剪報站首頁、待審表、草稿／文章頁。"""


def css_base() -> str:
    """變數、底色、字型、連結。"""
    return """
  :root {
    --bg: #f4f2ee;
    --surface: #fffcf7;
    --surface-elev: #ffffff;
    --ink: #1c1917;
    --muted: #78716c;
    --muted2: #a8a29e;
    --border: #e7e5e0;
    --accent: #0f766e;
    --accent-soft: rgba(15, 118, 110, 0.12);
    --accent-hover: #0d5c56;
    --radius: 14px;
    --radius-sm: 8px;
    --shadow: 0 1px 0 rgba(28, 25, 23, 0.04), 0 4px 16px rgba(28, 25, 23, 0.06);
    --font-sans: ui-sans-serif, system-ui, "Segoe UI", "Noto Sans TC", "PingFang TC",
      "Microsoft JhengHei", sans-serif;
    --font-display: ui-serif, "Iowan Old Style", "Palatino Linotype", Palatino,
      "Noto Serif TC", "Source Han Serif TC", Georgia, "Times New Roman", serif;
  }
  *, *::before, *::after { box-sizing: border-box; }
  body {
    margin: 0;
    min-height: 100vh;
    font-family: var(--font-sans);
    font-size: 1rem;
    line-height: 1.65;
    color: var(--ink);
    background: var(--bg);
    background-image: radial-gradient(ellipse 120% 80% at 50% -20%, rgba(15, 118, 110, 0.08), transparent 55%);
    -webkit-font-smoothing: antialiased;
  }
  a {
    color: var(--accent);
    text-decoration: none;
    text-underline-offset: 0.12em;
  }
  a:hover { color: var(--accent-hover); text-decoration: underline; }
  code {
    font-family: ui-monospace, "Cascadia Code", "Segoe UI Mono", Consolas, monospace;
    font-size: 0.88em;
    background: rgba(28, 25, 23, 0.06);
    padding: 0.12em 0.35em;
    border-radius: 4px;
  }
"""


def css_shell(*, narrow: bool) -> str:
    """主內容區寬度。"""
    w = "40rem" if narrow else "min(54rem, 100% - 2rem)"
    return f"""
  main {{
    max-width: {w};
    margin: 0 auto;
    padding: clamp(1.5rem, 4vw, 2.75rem) 1rem 3rem;
  }}
"""


def css_index_specific() -> str:
    """首頁列表、統計區塊。"""
    return """
  .masthead {
    margin-bottom: 2rem;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid var(--border);
  }
  .masthead h1 {
    font-family: var(--font-display);
    font-size: clamp(1.55rem, 3.5vw, 2rem);
    font-weight: 600;
    letter-spacing: -0.02em;
    margin: 0 0 0.35rem;
    line-height: 1.2;
  }
  .sub {
    margin: 0;
    color: var(--muted);
    font-size: 0.95rem;
  }
  .stats {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 1rem;
  }
  .pill {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    background: var(--surface-elev);
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 0.35rem 0.85rem;
    font-size: 0.82rem;
    color: var(--muted);
    box-shadow: var(--shadow);
  }
  .pill strong { color: var(--ink); font-weight: 600; }
  .list-wrap {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    overflow: hidden;
  }
  .category-block + .category-block {
    border-top: 1px solid var(--border);
  }
  .category-title {
    margin: 0;
    padding: 0.85rem 1.15rem 0.45rem;
    font-family: var(--font-display);
    font-size: 1.08rem;
    font-weight: 600;
    letter-spacing: -0.02em;
    color: var(--ink);
    background: rgba(15, 118, 110, 0.06);
    border-bottom: 1px solid var(--border);
  }
  .category-title span { display: inline-block; }
  .post-list {
    list-style: none;
    margin: 0;
    padding: 0;
  }
  .post-list li {
    border-bottom: 1px solid var(--border);
    transition: background 0.15s ease;
  }
  .post-list li:last-child { border-bottom: none; }
  .post-list li:hover { background: rgba(15, 118, 110, 0.04); }
  .post-list a {
    display: block;
    padding: 0.95rem 1.15rem 0.35rem;
    font-weight: 500;
    color: var(--ink);
    text-decoration: none;
  }
  .post-list a:hover { color: var(--accent-hover); text-decoration: none; }
  .meta {
    display: block;
    padding: 0 1.15rem 0.95rem;
    font-size: 0.8rem;
    color: var(--muted2);
    letter-spacing: 0.02em;
  }
  .empty {
    margin: 0;
    padding: 2rem 1.25rem;
    color: var(--muted);
    text-align: center;
  }
  footer.time {
    margin-top: 2rem;
    font-size: 0.78rem;
    color: var(--muted2);
  }
"""


def css_review_specific() -> str:
    """待審表格。"""
    return """
  h1.page-title {
    font-family: var(--font-display);
    font-size: clamp(1.45rem, 3vw, 1.85rem);
    font-weight: 600;
    letter-spacing: -0.02em;
    margin: 0 0 1rem;
  }
  .help {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1rem 1.15rem;
    margin-bottom: 1.5rem;
    box-shadow: var(--shadow);
    font-size: 0.92rem;
    color: var(--muted);
  }
  .help p { margin: 0 0 0.5rem; }
  .help p:last-child { margin-bottom: 0; line-height: 1.55; }
  .table-card {
    background: var(--surface-elev);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    overflow: hidden;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.92rem;
  }
  thead { background: var(--accent-soft); }
  th {
    font-weight: 600;
    text-align: left;
    padding: 0.65rem 0.85rem;
    color: var(--ink);
    border-bottom: 1px solid var(--border);
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  td {
    padding: 0.75rem 0.85rem;
    border-bottom: 1px solid var(--border);
    vertical-align: top;
    color: var(--ink);
  }
  tbody tr:nth-child(even) { background: rgba(28, 25, 23, 0.02); }
  tbody tr:hover { background: rgba(15, 118, 110, 0.05); }
  tbody tr:last-child td { border-bottom: none; }
"""


def css_article_specific() -> str:
    """單篇文章／草稿。"""
    return """
  article.prose {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: clamp(1.25rem, 3vw, 2rem);
    box-shadow: var(--shadow);
  }
  .eyebrow {
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--accent);
    font-weight: 600;
    margin: 0 0 0.5rem;
  }
  article.prose h1 {
    font-family: var(--font-display);
    font-size: clamp(1.45rem, 3.8vw, 2rem);
    font-weight: 600;
    letter-spacing: -0.025em;
    line-height: 1.22;
    margin: 0 0 1.25rem;
  }
  .source-box {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 0.65rem 0.85rem;
    font-size: 0.88rem;
    margin-bottom: 1.35rem;
    word-break: break-all;
  }
  .source-box a { word-break: break-all; }
  hr {
    border: none;
    border-top: 1px solid var(--border);
    margin: 1.5rem 0;
  }
  article.prose p {
    margin: 0 0 1rem;
    max-width: 65ch;
  }
  article.prose p:last-of-type { margin-bottom: 0; }
  .digest-kicker {
    font-size: 0.88rem;
    color: var(--muted);
    margin: 0 0 0.75rem;
    max-width: 65ch;
  }
  ul.digest-bullets {
    margin: 0 0 1rem;
    padding-left: 1.35rem;
    max-width: 65ch;
  }
  ul.digest-bullets li { margin-bottom: 0.45rem; }
  p.digest-short {
    font-size: 0.95rem;
    color: var(--ink);
    margin: 0 0 1rem;
    max-width: 65ch;
  }
  footer.note {
    font-size: 0.8rem;
    color: var(--muted);
    margin-top: 1.25rem;
  }
"""
