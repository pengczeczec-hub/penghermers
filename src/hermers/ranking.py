from __future__ import annotations

import re
from datetime import datetime, timezone

from hermers.discover import FeedItem

# 標題加權：越可能牽動全市場／權值／資金與政策者分數越高（可重複命中累加，上限見 _cap_score）
_MARKET_IMPACT_TERMS: tuple[tuple[str, float], ...] = (
    # 政策／利率／央行
    ("聯準會", 14.0),
    ("Fed", 14.0),
    ("升息", 13.0),
    ("降息", 13.0),
    ("利率", 11.0),
    ("央行", 12.0),
    ("貨幣政策", 12.0),
    ("通膨", 9.0),
    # 匯率／資金面
    ("匯率", 10.0),
    ("新台幣", 9.0),
    ("台幣", 9.0),
    ("美元", 8.0),
    ("貶值", 8.0),
    ("升值", 8.0),
    # 指數／全市場
    ("加權", 11.0),
    ("櫃買", 10.0),
    ("大盤", 10.0),
    ("台股", 8.0),
    ("股市", 7.0),
    ("重挫", 10.0),
    ("崩", 9.0),
    ("漲停", 9.0),
    ("跌停", 9.0),
    ("爆量", 7.0),
    # 權值／晶圓龍頭
    ("台積", 12.0),
    ("台積電", 12.0),
    ("2330", 10.0),
    ("權值", 9.0),
    ("半導體", 8.0),
    # 基本面／事件
    ("營收", 9.0),
    ("財報", 9.0),
    ("法說", 9.0),
    ("EPS", 8.0),
    ("本業", 7.0),
    ("虧損", 8.0),
    ("轉盈", 8.0),
    ("轉虧", 8.0),
    ("合約", 7.0),
    ("訂單", 7.0),
    ("併購", 8.0),
    ("下市", 9.0),
    ("下櫃", 8.0),
    ("停牌", 9.0),
    ("警示", 8.0),
    ("分盤", 7.0),
    ("庫藏股", 7.0),
    ("除息", 7.0),
    ("除權", 7.0),
    ("股利", 7.0),
    ("配息", 7.0),
    ("增資", 7.0),
    ("減資", 8.0),
    # 籌碼／法人
    ("外資", 9.0),
    ("投信", 8.0),
    ("自營", 7.0),
    ("買超", 8.0),
    ("賣超", 8.0),
    ("調節", 7.0),
    # 主管機關
    ("金管會", 10.0),
    ("證交所", 9.0),
    ("櫃買中心", 9.0),
    # 地緣／貿易（易牽動風險情緒）
    ("關稅", 8.0),
    ("制裁", 8.0),
    ("禁令", 7.0),
)

# 「重大頭條」分流：同標題下略提高權重（與本站 section 對齊）
_DOMAIN_BOOST: dict[str, float] = {
    "tw_market_extra": 6.0,
    "tw_stock": 0.0,
}


def _recency_bonus(published: datetime | None, now: datetime) -> float:
    if published is None:
        return 0.0
    delta_h = (now - published.astimezone(timezone.utc)).total_seconds() / 3600.0
    if delta_h < 0:
        delta_h = 0.0
    # 24h 內略加分，超過 72h 趨近 0
    if delta_h <= 6:
        return 4.0
    if delta_h <= 24:
        return 3.0
    if delta_h <= 48:
        return 2.0
    if delta_h <= 72:
        return 1.0
    return 0.0


def _cap_score(raw: float, cap: float = 85.0) -> float:
    return min(raw, cap)


def market_impact_score(item: FeedItem, *, now: datetime | None = None) -> float:
    """標題＋來源分流＋時效加權；分數越高代表越可能影響市場／越值得進入每日精選。"""
    now = now or datetime.now(timezone.utc)
    t = item.title or ""
    lower = t.lower()
    score = _DOMAIN_BOOST.get(item.domain_id, 0.0)

    for needle, w in _MARKET_IMPACT_TERMS:
        if needle.isascii():
            if needle.lower() in lower:
                score += w
        else:
            if needle in t:
                score += w

    score += _recency_bonus(item.published, now)
    # 若標題明顯偏長篇分析／副刊，略降權（仍可能因關鍵字入選）
    if re.search(r"懶人包|懶人|圖表看|一文看懂|懶人圖", t):
        score -= 4.0

    return _cap_score(max(score, 0.0))


def merge_candidates(candidates: list[FeedItem]) -> list[FeedItem]:
    """同一 URL 只保留一筆，取市場影響分數較高者（通常對應較合適的分流）。"""
    best: dict[str, FeedItem] = {}
    for item in candidates:
        u = item.url.strip()
        prev = best.get(u)
        if prev is None:
            best[u] = item
            continue
        if market_impact_score(item) > market_impact_score(prev):
            best[u] = item
    return list(best.values())


def rank_for_digest(items: list[FeedItem], *, max_items: int, now: datetime | None = None) -> list[FeedItem]:
    """依市場影響力排序後取前 max_items；再以發布時間作為次要排序鍵。"""
    now = now or datetime.now(timezone.utc)
    scored = [(market_impact_score(it, now=now), it) for it in items]
    scored.sort(
        key=lambda x: (
            x[0],
            x[1].published or datetime.min.replace(tzinfo=timezone.utc),
        ),
        reverse=True,
    )
    return [it for _, it in scored[:max_items]]
