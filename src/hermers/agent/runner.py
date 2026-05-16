from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

import yaml

from hermers.agent import brain
from hermers.agent.rules import route as rules_route
from hermers.agent.tools import run_tool, tools_schema_text
from hermers.executor import RunResult
from hermers.paths import repo_root


def _telegram_html(text: str) -> str:
    t = (text or "").strip()
    if not t:
        return "（無文字回覆）"
    if re.search(r"</?(?:b|code|pre|i|a|ul|li)\b", t, re.I):
        return t
    return html.escape(t)


def _persona() -> str:
    path = repo_root() / "config" / "agent.yaml"
    if path.is_file():
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return str(raw.get("persona") or "")
    return "你是 Hermes，使用者的專屬數位員工。"


def _max_rounds() -> int:
    path = repo_root() / "config" / "agent.yaml"
    if path.is_file():
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return int(raw.get("max_tool_rounds") or 5)
    return 5


class AgentRunner:
    """萬用 Agent：規則路由 + 可選 LLM 選工具，一律直接執行。"""

    def handle(self, user_text: str) -> RunResult:
        text = (user_text or "").strip()
        if not text:
            return RunResult(True, "請告訴我您要做什麼。")

        ruled = rules_route(text)
        if ruled is not None:
            return ruled

        if not brain.llm_available():
            from hermers.agent.cursor_brain import cursor_ready

            _, hint = cursor_ready()
            return RunResult(
                True,
                "<b>Hermes</b>（規則模式）\n"
                "可理解：部署、推送、剪報、貼網址、狀態。\n\n"
                "啟用 Cursor 大腦：\n"
                "1. 到 Cursor 儀表板 Integrations 建立 <code>CURSOR_API_KEY</code>\n"
                "2. 寫入 .env\n"
                "3. 執行 <code>install-cursor-brain.bat</code>\n"
                f"（{html.escape(hint)}）",
            )

        tools_txt = tools_schema_text()
        persona = _persona()
        history: list[dict[str, str]] = []
        current = text

        for _ in range(_max_rounds()):
            try:
                action = brain.chat_with_tools(
                    current,
                    tools_text=tools_txt,
                    persona=persona,
                    history=history,
                )
            except Exception as exc:  # noqa: BLE001
                return RunResult(
                    False,
                    f"<b>AI 無法回應</b>，需介入：\n<code>{html.escape(str(exc))}</code>",
                )

            if action.get("action") == "reply":
                reply = _telegram_html(str(action.get("text") or ""))
                return RunResult(True, reply)

            if action.get("action") == "tool":
                name = str(action.get("name") or "")
                args = action.get("args") or {}
                if not isinstance(args, dict):
                    args = {}
                result = run_tool(name, args)
                if not result.ok:
                    return result
                history.append({"role": "user", "content": current})
                history.append(
                    {
                        "role": "assistant",
                        "content": f"工具 {name} 結果：{result.message[:500]}",
                    }
                )
                current = f"工具 {name} 已執行完成。請用繁體中文向使用者總結結果。"
                continue

            return RunResult(True, str(action))

        return RunResult(True, "已達單次對話工具次數上限，請拆分任務再試。")
