"""英文摘要 → 繁體中文：LibreTranslate 優先，失敗段落由 Cursor LLM batch 備援。"""

from __future__ import annotations

import os
from typing import Sequence

import httpx

from hermers.env_load import load_dotenv


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
