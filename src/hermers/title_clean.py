"""新聞標題清理：移除媒體站名後綴與多餘分隔符。"""

from __future__ import annotations

# 長字串先替換，避免部分殘留
_TITLE_STRIP_FRAGMENTS = (
    "鉅亨網 - 台股新聞",
    "鉅亨網",
    " - 台股新聞",
)

_EDGE_CHARS = "-｜|·—"


def clean_news_title(title: str | None) -> str:
    if not title:
        return ""
    t = title.strip()
    for frag in _TITLE_STRIP_FRAGMENTS:
        t = t.replace(frag, "")
    t = t.strip()
    while t and t[0] in _EDGE_CHARS:
        t = t[1:].strip()
    while t and t[-1] in _EDGE_CHARS:
        t = t[:-1].strip()
    return t
