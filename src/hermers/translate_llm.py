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


def llm_en_to_zh_title(title: str) -> str | None:
    if not title.strip():
        return None
    if not llm_translate_available():
        return None
    user = json.dumps({"title": title.strip()[:500]}, ensure_ascii=False)
    system = """將 JSON 內的英文 "title" 譯為繁體中文標題（台灣新聞標題風格，簡潔）。
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
    system = """將 JSON 內的中文 "title" 譯為英文標題（簡潔、適合新聞網站側邊標題）。
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
