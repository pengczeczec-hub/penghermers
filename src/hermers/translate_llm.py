"""剪報內文／標題：Cursor LLM 英↔繁 batch 翻譯（LibreTranslate 失敗時備援）。"""

from __future__ import annotations

import json
import os
import re
import subprocess
from typing import Any

from hermers.agent.cursor_brain import cursor_chat, cursor_ready
from hermers.env_load import load_dotenv


def llm_translate_available() -> bool:
    load_dotenv()
    v = os.environ.get("HERMERS_TRANSLATE_LLM", "1").strip().lower()
    if v in ("0", "false", "no", "off"):
        return False
    return cursor_ready()[0]


def _extract_json_dict(text: str) -> dict[str, Any] | None:
    s = text.strip()
    if s.startswith("```"):
        lines = s.split("\n")
        if len(lines) >= 2 and lines[-1].strip() == "```":
            s = "\n".join(lines[1:-1]).strip()
        else:
            s = "\n".join(lines[1:]).strip()
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    start = s.find("{")
    end = s.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        obj = json.loads(s[start : end + 1])
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


def llm_batch_en_to_zh(paragraphs: list[str]) -> list[str] | None:
    """英→繁：一次傳多段，回傳同長度繁中列表；失敗回傳 None。"""
    if not paragraphs:
        return []
    if not llm_translate_available():
        return None
    user = json.dumps({"paragraphs": paragraphs}, ensure_ascii=False)
    system = """你是專業新聞編譯。使用者會傳入 JSON：{"paragraphs":["英文段落", ...]}。
請把每段翻成繁體中文（台灣用語），剪報體、簡潔通順。保留專有名詞、產品名、縮寫與 URL 可不硬譯。
段落數量必須與輸入相同：不可刪段、不可合併、不可拆成更多段。
僅輸出一個 JSON 物件，格式：{"paragraphs":["繁中段落", ...]}，不要 markdown 或其他說明。"""
    try:
        result = cursor_chat(user, system=system, history=None, timeout_sec=180)
    except (RuntimeError, OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None
    text = str(result.get("text") or "")
    obj = _extract_json_dict(text)
    if not obj:
        return None
    out = obj.get("paragraphs")
    if not isinstance(out, list) or len(out) != len(paragraphs):
        return None
    cleaned: list[str] = []
    for x in out:
        s = (str(x) if x is not None else "").strip()
        if not s:
            return None
        cleaned.append(s)
    return cleaned


def llm_batch_zh_to_en(paragraphs: list[str]) -> list[str] | None:
    """繁→英：一次傳多段，回傳同長度英文列表；失敗回傳 None。"""
    if not paragraphs:
        return []
    if not llm_translate_available():
        return None
    user = json.dumps({"paragraphs": paragraphs}, ensure_ascii=False)
    system = """你是專業新聞編譯。使用者會傳入 JSON：{"paragraphs":["繁體中文段落", ...]}。
請把每段翻成英文，簡潔通順，適合科技／新聞剪報。保留專有名詞、產品名、縮寫與 URL。
段落數量必須與輸入相同：不可刪段、不可合併、不可拆成更多段。
僅輸出一個 JSON 物件，格式：{"paragraphs":["英文段落", ...]}，不要 markdown 或其他說明。"""
    try:
        result = cursor_chat(user, system=system, history=None, timeout_sec=180)
    except (RuntimeError, OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None
    text = str(result.get("text") or "")
    obj = _extract_json_dict(text)
    if not obj:
        return None
    out = obj.get("paragraphs")
    if not isinstance(out, list) or len(out) != len(paragraphs):
        return None
    cleaned: list[str] = []
    for x in out:
        s = (str(x) if x is not None else "").strip()
        if not s:
            return None
        cleaned.append(s)
    return cleaned


def llm_en_to_zh_title(title: str) -> str | None:
    if not title.strip():
        return None
    if not llm_translate_available():
        return None
    user = json.dumps({"title": title.strip()[:500]}, ensure_ascii=False)
    system = """你是台灣財經媒體標題編輯。JSON 內的 "title" 為外文／英文來源標題，請勿逐字直譯或照抄。
請依其核心訊息，用你自己的話改寫成繁體中文標題（台灣讀者常用口吻、簡潔、15～35 字為宜）。
禁止複製原標題當作一字不漏的翻譯結果。
僅輸出：{"title":"..."}，不要其他文字。"""
    try:
        result = cursor_chat(user, system=system, history=None, timeout_sec=60)
    except (RuntimeError, OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None
    obj = _extract_json_dict(str(result.get("text") or ""))
    if not obj:
        return None
    t = obj.get("title")
    if not isinstance(t, str):
        return None
    t = t.strip()
    return t if t else None


def llm_zh_to_en_title(title: str) -> str | None:
    if not title.strip():
        return None
    if not llm_translate_available():
        return None
    user = json.dumps({"title": title.strip()[:500]}, ensure_ascii=False)
    system = """你是英文財經標題編輯。JSON 內為繁體中文標題；請勿只做機械式逐字英譯。
請依訊息核心改寫成自然、簡潔的英文標題（適合新聞列表），不要生硬照搬中文句式。
僅輸出：{"title":"..."}，不要其他文字。"""
    try:
        result = cursor_chat(user, system=system, history=None, timeout_sec=60)
    except (RuntimeError, OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None
    obj = _extract_json_dict(str(result.get("text") or ""))
    if not obj:
        return None
    t = obj.get("title")
    if not isinstance(t, str):
        return None
    t = re.sub(r"\s+", " ", t).strip()
    return t if t else None


def _clip_paragraph_list(paragraphs: list[str], *, each_max: int = 900, total_max: int = 10000) -> list[str]:
    out: list[str] = []
    n = 0
    for raw in paragraphs:
        piece = raw.strip()
        if not piece:
            continue
        if len(piece) > each_max:
            piece = piece[:each_max]
        if n + len(piece) > total_max:
            rest = total_max - n
            if rest > 80:
                out.append(piece[:rest])
            break
        out.append(piece)
        n += len(piece) + 2
    return out


def llm_bilingual_clipping_digest(
    *,
    rss_title: str,
    page_title: str,
    paragraphs: list[str],
) -> dict[str, Any] | None:
    """依擷取片段產出「改寫標題 + 雙語重點條列」，避免發布全文。"""
    clipped = _clip_paragraph_list(paragraphs)
    if not clipped:
        return None
    if not llm_translate_available():
        return None
    user = json.dumps(
        {
            "rss_title": rss_title.strip()[:400],
            "page_title": page_title.strip()[:400],
            "excerpt_paragraphs": clipped,
        },
        ensure_ascii=False,
    )
    system = """你是台股／財經剪報助理。使用者會傳入 JSON：
{"rss_title":"...", "page_title":"...", "excerpt_paragraphs":["擷取之段落（可能不完整）", ...]}

法律與編輯準則（務必遵守）：
1) 絕對不可輸出原文全文、長篇逐句抄寫或大段引號引用；只能根據素材「重新表述」事實重點。
2) bullets_zh 與 bullets_en 各為 3～5 條，一事一點；每條獨立一句，各自不超過約 120 個英文字母或約 80 個繁體中文字的閱讀長度（過長請濃縮）。
3) title_zh、title_en：請依 rss_title 與內文訊息「各自改寫」為新標題（台灣讀者口吻／自然英文標題），勿複製 rss_title 或 page_title 原文當成品。
4) 可選 short_zh、short_en：若填寫，須為「一段」總結，各不超過 150 字（英文為 150 characters 以內）；若無把握可輸出空字串。
5) bullets_zh 與 bullets_en 條數必須相同且語意對應。

僅輸出一個 JSON 物件，格式如下（不要 markdown）：
{"title_zh":"...","title_en":"...","bullets_zh":["..."],"bullets_en":["..."],"short_zh":"","short_en":""}
"""
    try:
        result = cursor_chat(user, system=system, history=None, timeout_sec=180)
    except (RuntimeError, OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None
    obj = _extract_json_dict(str(result.get("text") or ""))
    if not obj:
        return None
    tz = obj.get("title_zh")
    te = obj.get("title_en")
    bz = obj.get("bullets_zh")
    be = obj.get("bullets_en")
    if not isinstance(tz, str) or not isinstance(te, str):
        return None
    tz, te = tz.strip(), te.strip()
    if not tz or not te:
        return None
    if not isinstance(bz, list) or not isinstance(be, list):
        return None
    if len(bz) != len(be) or len(bz) < 3 or len(bz) > 5:
        return None
    clean_zh: list[str] = []
    clean_en: list[str] = []
    for x, y in zip(bz, be):
        sx = (str(x) if x is not None else "").strip()
        sy = (str(y) if y is not None else "").strip()
        if not sx or not sy:
            return None
        clean_zh.append(sx)
        clean_en.append(sy)
    sz = obj.get("short_zh", "")
    se = obj.get("short_en", "")
    short_zh = (str(sz).strip()[:220]) if isinstance(sz, str) else ""
    short_en = (str(se).strip()[:220]) if isinstance(se, str) else ""
    if len(short_zh) > 150:
        short_zh = short_zh[:150].rstrip() + "…"
    if len(short_en) > 150:
        short_en = short_en[:149].rstrip() + "…"
    from hermers.translate_body import snippet_looks_mostly_english, translate_zh_to_en

    fixed_en: list[str] = []
    for zh_b, en_b in zip(clean_zh, clean_en):
        if snippet_looks_mostly_english(en_b):
            fixed_en.append(en_b)
            continue
        lt = translate_zh_to_en(zh_b)
        if lt and snippet_looks_mostly_english(lt):
            fixed_en.append(lt.strip())
        else:
            fixed_en.append(en_b)
    clean_en = fixed_en
    if short_zh and short_en and not snippet_looks_mostly_english(short_en):
        st = translate_zh_to_en(short_zh)
        if st and snippet_looks_mostly_english(st):
            short_en = st.strip()[:220]
            if len(short_en) > 150:
                short_en = short_en[:149].rstrip() + "…"
    return {
        "title_zh": tz,
        "title_en": te,
        "bullets_zh": clean_zh,
        "bullets_en": clean_en,
        "short_zh": short_zh,
        "short_en": short_en,
    }
