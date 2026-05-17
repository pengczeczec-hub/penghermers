"""Telegram 對話記憶（本機 JSON，最近 N 則）。"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from hermers.paths import data_dir

_MAX_MESSAGES = 20


def _path():
    return data_dir() / "telegram_chat_history.json"


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


class ChatMemory:
    def __init__(self, *, max_messages: int = _MAX_MESSAGES) -> None:
        self.max_messages = max_messages

    def _load_all(self) -> dict[str, list[dict[str, str]]]:
        path = _path()
        if not path.is_file():
            return {}
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        if not isinstance(raw, dict):
            return {}
        return raw

    def _save_all(self, data: dict[str, list[dict[str, str]]]) -> None:
        data_dir().mkdir(parents=True, exist_ok=True)
        _path().write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get(self, chat_id: int | str) -> list[dict[str, str]]:
        key = str(chat_id)
        rows = self._load_all().get(key) or []
        out: list[dict[str, str]] = []
        for row in rows[-self.max_messages :]:
            role = str(row.get("role", "user"))
            content = str(row.get("content", "")).strip()
            if content:
                out.append({"role": role, "content": content})
        return out

    def append(self, chat_id: int | str, role: str, content: str) -> None:
        key = str(chat_id)
        data = self._load_all()
        rows = list(data.get(key) or [])
        rows.append(
            {
                "role": role,
                "content": _strip_html(content)[:4000],
                "ts": datetime.now(timezone.utc).isoformat(),
            }
        )
        data[key] = rows[-self.max_messages :]
        self._save_all(data)

    def clear(self, chat_id: int | str) -> None:
        key = str(chat_id)
        data = self._load_all()
        if key in data:
            del data[key]
            self._save_all(data)
