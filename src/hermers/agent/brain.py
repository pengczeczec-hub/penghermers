from __future__ import annotations

import os
from typing import Any

import yaml

from hermers.agent.cursor_brain import cursor_chat, cursor_ready
from hermers.env_load import load_dotenv
from hermers.paths import repo_root


def _load_agent_config() -> dict:
    path = repo_root() / "config" / "agent.yaml"
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _provider() -> str:
    load_dotenv()
    cfg = _load_agent_config()
    return (
        os.environ.get("HERMES_LLM_PROVIDER")
        or (cfg.get("llm") or {}).get("provider")
        or "cursor"
    ).lower()


def llm_available() -> bool:
    p = _provider()
    if p in ("none", "off", ""):
        return False
    if p == "cursor":
        return cursor_ready()[0]
    # 舊版相容：openai / ollama（不建議，使用者要 Cursor API）
    if p == "openai":
        return bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("HERMES_LLM_API_KEY"))
    if p == "ollama":
        return True
    return cursor_ready()[0]


def chat_with_tools(
    user_text: str,
    *,
    tools_text: str,
    persona: str,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    provider = _provider()
    system = f"""{persona.strip()}

可用工具：
{tools_text}

回覆格式（僅輸出 JSON，不要 markdown 程式碼區塊）：
1) 需執行工具：{{"action":"tool","name":"工具名","args":{{}}}}
2) 僅文字回覆：{{"action":"reply","text":"繁體中文內容"}}
"""

    if provider == "cursor":
        return cursor_chat(user_text, system=system, history=history)

    if provider in ("none", "off"):
        raise RuntimeError("LLM 已關閉")

    raise RuntimeError(
        f"提供者 {provider} 已停用。請設 HERMES_LLM_PROVIDER=cursor 與 CURSOR_API_KEY。"
    )
