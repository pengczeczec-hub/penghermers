from __future__ import annotations

import html
import json
import re
import time

import httpx

from hermers.agent.runner import AgentRunner
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

<b>自然語言</b>（例）
「幫我部署網站」「抓今日熱門科技新聞」「這則新聞做成剪報」+ 網址

<b>萬用 AI</b>：使用 <b>Cursor API</b>（CURSOR_API_KEY），消耗 Cursor 訂閱額度，非 GPT/OpenAI。"""

_EXEC = HermesExecutor()
_AGENT = AgentRunner()


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


def handle_message(text: str) -> str:
    text = (text or "").strip()

    if text.startswith("/"):
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower().split("@")[0]
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd in ("/help", "/start"):
            return HELP_TEXT
        if cmd == "/status":
            return _EXEC.status().message
        if cmd == "/pipeline":
            return _EXEC.run_pipeline(push=False).message
        if cmd == "/publish":
            return _EXEC.publish().message
        if cmd == "/deploy":
            urls = _extract_urls(arg)
            if urls:
                return _EXEC.ingest_url(urls[0], push=True).message
            return _EXEC.deploy().message
        if cmd in ("/cancel", "/reset"):
            return (
                "<b>已重置</b>\n"
                "本輪不會再重跑舊指令。一般對話可直接輸入需求；"
                "查網址請傳 <code>/status</code> 或問「網站網址」。"
            )
        return "未知指令。傳 /help"

    return _AGENT.handle(text).message


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
                reply = handle_message(text)
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
