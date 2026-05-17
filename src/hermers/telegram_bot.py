from __future__ import annotations

import html
import json
import re
import time

import httpx

from hermers.agent.runner import AgentRunner
from hermers.chat_memory import ChatMemory
from hermers.env_load import load_dotenv
from hermers.executor import HermesExecutor
from hermers.paths import data_dir
from hermers.telegram_notify import send_message

HELP_TEXT = """<b>Hermes · 您的專屬員工</b>

我會<b>直接在本機執行</b>，不是只提醒您開檔案。

<b>快速指令</b>
/deploy — 部署（push + Cloudflare）
/publish — 推 GitHub
/pipeline — 自動剪報
/status — 狀態
/beautify — 美化首頁 UI
/reset — 清空對話記憶（20 則）

<b>自然語言</b>（例）
「幫我部署網站」「抓今日熱門科技新聞」「這則新聞做成剪報」+ 網址

<b>萬用 AI</b>：使用 <b>Cursor API</b>（CURSOR_API_KEY），消耗 Cursor 訂閱額度，非 GPT/OpenAI。"""

_EXEC = HermesExecutor()
_AGENT = AgentRunner()
_MEMORY = ChatMemory(max_messages=20)


def _offset_path():
    return data_dir() / "telegram_offset.json"


def _load_offset() -> int:
    path = _offset_path()
    if not path.is_file():
        return 0
    return int(json.loads(path.read_text(encoding="utf-8")).get("offset", 0))


def _save_offset(offset: int) -> None:
    data_dir().mkdir(parents=True, exist_ok=True)
    _offset_path().write_text(json.dumps({"offset": offset}), encoding="utf-8")


def _api_get(token: str, method: str, **params: object) -> dict:
    url = f"https://api.telegram.org/bot{token}/{method}"
    with httpx.Client(timeout=60.0) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


def _authorized(chat_id: int, allowed: str) -> bool:
    return str(chat_id) == str(allowed).strip()


def _extract_urls(text: str) -> list[str]:
    return re.findall(r"https?://\S+", text)


def _remember(chat_id: int | str | None, user_text: str, reply: str) -> str:
    if chat_id is not None:
        _MEMORY.append(chat_id, "user", user_text)
        _MEMORY.append(chat_id, "assistant", reply)
    return reply


def handle_message(text: str, *, chat_id: int | str | None = None) -> str:
    text = (text or "").strip()

    if text.startswith("/"):
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower().split("@")[0]
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ("/help", "/start"):
            return _remember(chat_id, text, HELP_TEXT)
        if cmd == "/status":
            return _remember(chat_id, text, _EXEC.status().message)
        if cmd == "/pipeline":
            return _remember(chat_id, text, _EXEC.run_pipeline(push=False).message)
        if cmd == "/publish":
            return _remember(chat_id, text, _EXEC.publish().message)
        if cmd == "/deploy":
            urls = _extract_urls(arg)
            if urls:
                msg = _EXEC.ingest_url(urls[0], push=True).message
            else:
                msg = _EXEC.deploy().message
            return _remember(chat_id, text, msg)
        if cmd == "/beautify":
            from hermers.local_actions import beautify_site_ui

            return _remember(chat_id, text, beautify_site_ui().message)
        if cmd in ("/cancel", "/reset"):
            if chat_id is not None:
                _MEMORY.clear(chat_id)
            return (
                "<b>已重置</b>\n"
                "對話記憶已清空（最近 20 則）。可重新下指令；"
                "查網址請傳 <code>/status</code>。"
            )
        return _remember(chat_id, text, "未知指令。傳 /help")

    return _remember(chat_id, text, _dispatch(text, chat_id=chat_id))


def _dispatch(text: str, *, chat_id: int | str | None) -> str:
    history = _MEMORY.get(chat_id) if chat_id is not None else []
    return _AGENT.handle(text, history=history).message


def run_bot(*, poll_seconds: float = 2.0) -> None:
    load_dotenv()
    import os

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    allowed = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not allowed:
        raise SystemExit("請在 .env 設定 TELEGRAM_BOT_TOKEN 與 TELEGRAM_CHAT_ID")

    print("Hermes Agent（直接執行 + 可選 LLM）")
    print(f"chat_id={allowed}  Ctrl+C 結束\n")

    offset = _load_offset()
    while True:
        try:
            data = _api_get(token, "getUpdates", offset=offset, timeout=30)
        except httpx.HTTPError as exc:
            print(f"輪詢錯誤：{exc}")
            time.sleep(poll_seconds)
            continue

        for upd in data.get("result") or []:
            offset = max(offset, int(upd["update_id"]) + 1)
            msg = upd.get("message") or {}
            chat = msg.get("chat") or {}
            chat_id = chat.get("id")
            text = msg.get("text") or ""
            if chat_id is None or not _authorized(int(chat_id), allowed):
                continue
            print(f"← {text[:80]}")
            try:
                reply = handle_message(text, chat_id=int(chat_id))
            except Exception as exc:  # noqa: BLE001
                reply = f"<b>系統錯誤，需介入</b>\n<code>{html.escape(str(exc))}</code>"
            if send_message(reply):
                print("→ 已回覆")
            else:
                print("→ 回覆產生成功，但 Telegram 發送失敗（見上方錯誤說明）")
        _save_offset(offset)
        time.sleep(poll_seconds)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--poll", type=float, default=2.0)
    args = parser.parse_args()
    run_bot(poll_seconds=args.poll)


if __name__ == "__main__":
    main()
