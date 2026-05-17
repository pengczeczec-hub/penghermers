"""英文摘要 → 繁體中文：選用 LibreTranslate 相容 API（可自建或用公開節點）。"""

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
    """逐段嘗試翻譯；失敗則標註並保留原文供編輯。"""
    paras = [p.strip() for p in paragraphs if p and p.strip()]
    if not paras:
        return []

    translated: list[str | None] = []
    any_ok = False
    fail_tag_zh = "〔此段自動繁體翻譯未成功，下方為英文原文；請於送審前改寫為繁體剪報體。〕"
    for p in paras:
        clip = p[:12000]
        t = translate_en_to_zh(clip)
        if t and t != clip:
            translated.append(t)
            any_ok = True
        else:
            translated.append(None)

    if not any_ok:
        banner = (
            "（目前無法連線自動翻譯服務；中文版區塊暫附英文原文，請於通過審核前改寫為繁體中文，"
            "或設定 LIBRETRANSLATE_URL／API。）"
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
    t = translate_en_to_zh(title.strip()[:500])
    return t if t else title.strip()
