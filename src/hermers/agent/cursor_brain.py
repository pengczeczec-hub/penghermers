from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from hermers.env_load import load_dotenv
from hermers.paths import repo_root
from hermers.subprocess_utf8 import run as sp_run
from hermers.subprocess_utf8 import utf8_env


def _bridge_dir() -> Path:
    return repo_root() / "tools" / "cursor_brain"


def cursor_ready() -> tuple[bool, str]:
    load_dotenv()
    if not os.environ.get("CURSOR_API_KEY", "").strip():
        return False, "未設定 CURSOR_API_KEY（Cursor 儀表板 → Integrations）"
    if not shutil.which("node"):
        return False, "未安裝 Node.js（需執行 install-cursor-brain.bat）"
    script = _bridge_dir() / "prompt.mjs"
    if not script.is_file():
        return False, "缺少 tools/cursor_brain/prompt.mjs"
    if not (_bridge_dir() / "node_modules" / "@cursor" / "sdk").is_dir():
        return False, "請執行 install-cursor-brain.bat 安裝 @cursor/sdk"
    return True, "ok"


def _model_id() -> str:
    load_dotenv()
    import yaml

    path = repo_root() / "config" / "agent.yaml"
    model = "composer-2"
    if path.is_file():
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        model = (raw.get("llm") or {}).get("model") or model
    return os.environ.get("HERMES_CURSOR_MODEL") or model


def cursor_chat(
    user_text: str,
    *,
    system: str,
    history: list[dict[str, str]] | None = None,
    timeout_sec: int = 600,
) -> dict[str, Any]:
    """呼叫 Cursor SDK 本機 Agent（消耗 Cursor 帳號額度，非 OpenAI）。"""
    ok, reason = cursor_ready()
    if not ok:
        raise RuntimeError(reason)

    parts: list[str] = []
    if history:
        for msg in history[-6:]:
            role = msg.get("role", "user")
            parts.append(f"[{role}]\n{msg.get('content', '')}")
    parts.append(f"[user]\n{user_text}")
    combined_user = "\n\n".join(parts)

    payload = {
        "system": system,
        "user": combined_user,
        "cwd": str(repo_root()),
        "model": _model_id(),
    }
    env = utf8_env()
    proc = sp_run(
        ["node", "prompt.mjs"],
        input=json.dumps(payload, ensure_ascii=False),
        cwd=_bridge_dir(),
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        env=env,
    )
    if proc.stdout.strip():
        try:
            data = json.loads(proc.stdout.strip().splitlines()[-1])
        except json.JSONDecodeError:
            data = {"ok": False, "error": proc.stdout[:500]}
    else:
        data = {"ok": False, "error": proc.stderr or "無輸出"}

    if proc.returncode != 0 and data.get("ok") is not True:
        err = data.get("error") or proc.stderr or f"exit {proc.returncode}"
        raise RuntimeError(err)

    text = str(data.get("text") or "")
    return _parse_action(text)


def _parse_action(content: str) -> dict[str, Any]:
    import re

    content = content.strip()
    block = re.search(r"\{[\s\S]*\}", content)
    if block:
        try:
            data = json.loads(block.group(0))
            if isinstance(data, dict) and data.get("action"):
                return data
        except json.JSONDecodeError:
            pass
    return {"action": "reply", "text": content}
