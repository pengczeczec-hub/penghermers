"""英文摘要 → 繁體中文：LibreTranslate 優先，失敗段落由 Cursor LLM batch 備援。"""

from __future__ import annotations

import os
from typing import Sequence

import httpx

from hermers.env_load import load_dotenv


def snippet_looks_mostly_english(s: str) -> bool:
    """短句／條列：是否以英文字母為主（避免誤把英文欄填成繁中）。"""
    s = s.strip()
    if not s:
        return True
    cjk = sum(1 for c in s if "\u4e00" <= c <= "\u9fff")
    latin = sum(1 for c in s if "a" <= c.lower() <= "z")
    if cjk == 0 and latin == 0:
        return True
    if latin < 6 and cjk >= 8:
        return False
    return latin >= cjk * 1.1 or (latin >= 12 and cjk <= max(18, latin // 2))


def passage_looks_mostly_english(s: str) -> bool:
    """長篇正文：是否整體像英文（用於偵測英文欄仍為繁中的舊稿）。"""
    s = " ".join(s.split())
    if not s:
        return True
    if len(s) < 160:
        return snippet_looks_mostly_english(s)
    cjk = sum(1 for c in s if "\u4e00" <= c <= "\u9fff")
    latin = sum(1 for c in s if "a" <= c.lower() <= "z")
    if latin < 25:
        return False
    return cjk <= latin * 0.5


def _translate_enabled() -> bool:
    load_dotenv()
    v = os.environ.get("HERMERS_TRANSLATE", "1").strip().lower()
    return v not in ("0", "false", "no", "off")


def translate_en_to_zh(text: str, *, timeout: float = 28.0) -> str | None:
    """將單段文字英譯中（LibreTranslate API）；失敗回傳 None。"""
    text = text.strip()
    if not text:
        return text
    if not _translate_enabled():
        return None

    load_dotenv()
    url = os.environ.get("LIBRETRANSLATE_URL", "https://libretranslate.de/translate").strip()
    api_key = os.environ.get("LIBRETRANSLATE_API_KEY", "").strip()
    target = os.environ.get("HERMERS_TRANSLATE_TARGET", "zh").strip() or "zh"
    payload: dict[str, str] = {"q": text[:12000], "source": "en", "target": target, "format": "text"}
    if api_key:
        payload["api_key"] = api_key

    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.post(url, json=payload)
            if r.status_code != 200:
                return None
            data = r.json()
            if not isinstance(data, dict):
                return None
            out = data.get("translatedText")
            return out.strip() if isinstance(out, str) and out.strip() else None
    except (httpx.HTTPError, ValueError, TypeError):
        return None


def translate_zh_to_en(text: str, *, timeout: float = 28.0) -> str | None:
    """單段繁中→英文（LibreTranslate）；失敗回傳 None。"""
    text = text.strip()
    if not text:
        return text
    if not _translate_enabled():
        return None

    load_dotenv()
    url = os.environ.get("LIBRETRANSLATE_URL", "https://libretranslate.de/translate").strip()
    api_key = os.environ.get("LIBRETRANSLATE_API_KEY", "").strip()
    # 多數實例以 zh 為中文來源；若失敗可改環境變數
    source = os.environ.get("HERMERS_LT_SOURCE_ZH", "zh").strip() or "zh"
    payload: dict[str, str] = {"q": text[:12000], "source": source, "target": "en", "format": "text"}
    if api_key:
        payload["api_key"] = api_key

    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.post(url, json=payload)
            if r.status_code != 200:
                return None
            data = r.json()
            if not isinstance(data, dict):
                return None
            out = data.get("translatedText")
            return out.strip() if isinstance(out, str) and out.strip() else None
    except (httpx.HTTPError, ValueError, TypeError):
        return None


def en_paragraphs_from_zh_sequence(paragraphs: Sequence[str]) -> list[str] | None:
    """逐段 zh→en（LibreTranslate）；任一段失敗或結果仍像中文則回傳 None。"""
    paras = [p.strip() for p in paragraphs if p and p.strip()]
    if not paras:
        return []
    out: list[str] = []
    for p in paras:
        clip = p[:12000]
        t = translate_zh_to_en(clip) if _translate_enabled() else None
        if not t or not t.strip():
            return None
        if not snippet_looks_mostly_english(t):
            return None
        out.append(t.strip())
    return out


def zh_paragraphs_from_extract(paragraphs: Sequence[str]) -> list[str]:
    """逐段 LibreTranslate；失敗段落改由 Cursor LLM batch 補齊；仍失敗則標註並保留原文。"""
    paras = [p.strip() for p in paragraphs if p and p.strip()]
    if not paras:
        return []

    translated: list[str | None] = []
    fail_tag_zh = "〔此段自動繁體翻譯未成功，下方為英文原文；請於送審前改寫為繁體剪報體。〕"
    for p in paras:
        clip = p[:12000]
        t = translate_en_to_zh(clip) if _translate_enabled() else None
        if t and t != clip:
            translated.append(t)
        else:
            translated.append(None)

    if any(z is None for z in translated):
        from hermers.translate_llm import llm_batch_en_to_zh, llm_translate_available

        if llm_translate_available():
            miss_idx = [i for i, z in enumerate(translated) if z is None]
            batch_in = [paras[i] for i in miss_idx]
            filled = llm_batch_en_to_zh(batch_in)
            if filled is not None and len(filled) == len(miss_idx):
                for j, idx in enumerate(miss_idx):
                    translated[idx] = filled[j]

    any_ok = any(z is not None for z in translated)
    if not any_ok:
        banner = (
            "（未能完成自動中譯：可檢查 LIBRETRANSLATE_URL，或設定 CURSOR_API_KEY "
            "並保留 HERMERS_TRANSLATE_LLM=1 以啟用 LLM 備援。中文版暫附英文原文，於送審前改寫為繁體。）"
        )
        return [banner, *paras]

    out: list[str] = []
    for raw, z in zip(paras, translated):
        if z is None:
            out.append(f"{fail_tag_zh}\n\n{raw}")
        else:
            out.append(z)
    return out


def zh_title_from_extract(title: str) -> str:
    """外文標題 → 繁體「改寫」標題（LibreTranslate／LLM）；若皆不可用則回退原文。"""
    s = title.strip()[:500]
    if not s:
        return ""
    if _translate_enabled():
        t = translate_en_to_zh(s)
        if t and t.strip() and t.strip() != s:
            return t.strip()
    from hermers.translate_llm import llm_en_to_zh_title

    lt = llm_en_to_zh_title(s)
    return lt if lt else s
