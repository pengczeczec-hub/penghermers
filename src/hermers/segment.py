"""首頁市場分頁：依標題／來源與 ID 推論 site_segment（tw / us / crypto / other）。"""

from __future__ import annotations

from dataclasses import dataclass

_VALID = frozenset({"tw", "us", "crypto", "other"})

# 繁中與常見英文關鍵字；權重由長度與專指性略調
_TW_NEEDLES: tuple[tuple[str, float], ...] = (
    ("台股", 2.5),
    ("台灣股市", 2.2),
    ("加權指數", 2.0),
    ("加權", 1.2),
    ("櫃買指數", 2.0),
    ("櫃買", 1.2),
    ("上市櫃", 1.8),
    ("上櫃", 1.2),
    ("上市", 0.6),
    ("興櫃", 1.4),
    ("除權除息", 1.5),
    ("除息", 1.0),
    ("除權", 1.0),
    ("營收速報", 2.2),
    ("台股大型", 2.5),
    ("台股中小型", 2.5),
    ("集中市場", 1.6),
    ("twse", 1.8),
    ("外資買超", 1.3),
    ("投信買超", 1.3),
    ("自營", 0.5),
    ("調整台股", 2.4),
    ("台股權重", 2.4),
    ("0050", 1.0),
    ("00919", 1.0),
    ("熱門股", 1.8),
)

_US_NEEDLES: tuple[tuple[str, float], ...] = (
    ("美股", 2.8),
    ("美國股市", 2.2),
    ("標普500", 2.2),
    ("標普", 1.4),
    ("s&p 500", 2.0),
    ("s&p", 1.2),
    ("sp500", 1.5),
    ("道瓊", 1.8),
    ("dow jones", 1.8),
    ("nasdaq", 1.8),
    ("那斯達克", 1.8),
    ("費城半導體", 1.6),
    ("費半", 1.4),
    ("聯準會", 1.8),
    ("fomc", 1.6),
    ("13f", 2.2),
    ("13-f", 2.0),
    ("橋水", 1.2),
    ("bridgewater", 1.4),
    ("波克夏", 1.3),
    ("berkshire", 1.4),
    ("巴菲特", 1.0),
    ("索羅斯", 1.2),
    ("soros", 1.2),
    ("美光", 0.5),
    ("輝達", 0.6),
    ("亞馬遜", 0.5),
    ("salesforce", 0.8),
)

_CRYPTO_NEEDLES: tuple[tuple[str, float], ...] = (
    ("加密貨幣", 2.8),
    ("虛擬貨幣", 2.6),
    ("數位資產", 2.0),
    ("比特幣", 2.6),
    ("bitcoin", 2.6),
    ("btc", 1.8),
    ("乙太", 2.4),
    ("以太坊", 2.6),
    ("ethereum", 2.6),
    ("以太幣", 2.4),
    ("solana", 2.0),
    ("山寨幣", 2.0),
    ("defi", 2.0),
    ("web3", 1.8),
    ("區塊鏈", 1.6),
    ("stablecoin", 2.2),
    ("穩定幣", 2.2),
    ("cbdc", 2.0),
    ("nft", 1.4),
)


def _score_needles(blob: str, blob_l: str, needles: tuple[tuple[str, float], ...]) -> float:
    s = 0.0
    for needle, w in needles:
        nl = needle.lower()
        if any("\u4e00" <= c <= "\u9fff" for c in needle):
            if needle in blob:
                s += w
        else:
            if nl in blob_l:
                s += w
    return s


def _topic_blob(meta: dict, *, slug: str) -> tuple[str, str]:
    parts = [
        meta.get("title"),
        meta.get("title_en"),
        meta.get("source_title"),
        slug or meta.get("id"),
        meta.get("url"),
        meta.get("domain_name"),
    ]
    blob = "\n".join(str(p or "") for p in parts)
    return blob, blob.lower()


@dataclass(frozen=True)
class SegmentAnalysis:
    primary: str
    tw: float
    us: float
    crypto: float


def analyze_site_segment(meta: dict, *, slug: str = "") -> SegmentAnalysis:
    """回傳 primary 與各題材得分（不依賴 meta 既有 site_segment）。"""
    blob, blob_l = _topic_blob(meta, slug=slug or "")
    tw = _score_needles(blob, blob_l, _TW_NEEDLES)
    us = _score_needles(blob, blob_l, _US_NEEDLES)
    crypto = _score_needles(blob, blob_l, _CRYPTO_NEEDLES)

    did = (meta.get("domain_id") or "").strip()
    if did == "tw_stock":
        tw += 0.35
    elif did == "tw_market_extra":
        tw += 0.15

    # 強規則（沿用並略擴充）
    if "營收速報" in blob and ("台股" in blob or "台股大型" in blob or "台股中小型" in blob):
        tw += 2.0
    if "美股" in blob or "13f" in blob_l or "13-f" in blob_l:
        us += 1.2

    primary = _pick_primary(tw, us, crypto)
    return SegmentAnalysis(primary=primary, tw=tw, us=us, crypto=crypto)


def _pick_primary(tw: float, us: float, crypto: float) -> str:
    """在未套用使用者鎖定時，決定 primary。"""
    # 加密題材明顯優先於股市標籤
    if crypto >= 2.2 and crypto >= tw + 0.35 and crypto >= us + 0.35:
        return "crypto"

    if tw >= 2.0 and us >= 2.0:
        if us > tw + 0.35:
            return "us"
        if tw >= us:
            return "tw"
        return "us"

    if us >= 2.0 and us > tw:
        return "us"
    if tw >= 2.0 and tw > us:
        return "tw"

    if tw > us and tw >= 1.0:
        return "tw"
    if us > tw and us >= 1.0:
        return "us"
    return "other"


def infer_site_segment(meta: dict, *, slug: str = "") -> str:
    """回傳 tw / us / crypto / other。若 meta 已有合法 site_segment 則沿用。"""
    raw = meta.get("site_segment")
    if isinstance(raw, str) and raw.strip().lower() in _VALID:
        return raw.strip().lower()

    return analyze_site_segment(meta, slug=slug).primary


def dual_tw_us_for_home(analysis: SegmentAnalysis) -> bool:
    """內容同時強相關台、美股市時，首頁可在「台股」「美股」標籤重複列出（仍須名次門檻）。"""
    if analysis.primary not in ("tw", "us"):
        return False
    return analysis.tw >= 2.0 and analysis.us >= 2.0
