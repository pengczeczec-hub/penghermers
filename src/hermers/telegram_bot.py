from __future__ import annotations

import json
import re
import time

import httpx

from hermers.cursor_tasks import create_task, list_tasks
from hermers.env_load import load_dotenv
from hermers.hermes_config import load_hermes_config
from hermers.paths import data_dir, repo_root
from hermers.shell_runner import verify_github_token
from hermers.telegram_notify import send_message

HELP_TEXT = """<b>Hermes × Cursor</b>

指令會建立 <b>Cursor 任務</b>（不直接呼叫外部 AI）。

/status — 狀態
/pipeline — 建立「剪報管線」任務
/publish — 建立「Git 推送」任務
/deploy — 建立「Cloudflare 部署」任務
/tasks — 列出待辦任務

請在電腦開啟 <b>Cursor</b> 處理 tasks/pending/ 內的 CURSOR_SPEC.md

任意文字 — 建立自訂 Cursor 任務"""


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


def handle_command(text: str) -> str:
    text = (text or "").strip()
    if not text.startswith("/"):
        folder = create_task(
            "user_request",
            title=text[:60],
            source="telegram",
            user_text=text,
        )
        return (
            f"已建立 Cursor 任務\n<code>{folder.name}</code>\n"
            f"請在 Cursor 開啟專案並執行 CURSOR_SPEC.md"
        )

    parts = text.split(maxsplit=1)
    cmd = parts[0].lower().split("@")[0]
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd in ("/help", "/start"):
        return HELP_TEXT
    if cmd == "/status":
        cfg = load_hermes_config()
        gh = verify_github_token()
        pending = list_tasks(cfg)
        gh_line = f"GitHub: {gh.get('login')}" if gh.get("ok") else "GitHub: 未設定 TOKEN"
        return (
            f"<b>Hermes</b>\n{gh_line}\n"
            f"待辦任務: {len(pending)}\n"
            f"專案: <code>{repo_root()}</code>"
        )
    if cmd == "/pipeline":
        f = create_task("digest_pipeline", title="剪報管線", source="telegram", user_text=arg)
        return f"已建立任務 <code>{f.name}</code>\n請在 Cursor 執行管線並審核 staging。"
    if cmd == "/publish":
        f = create_task("git_publish", title="Git 推送", source="telegram", user_text=arg)
        return f"已建立任務 <code>{f.name}</code>\n請在 Cursor 終端機執行推送（讀取 GITHUB_TOKEN）。"
    if cmd == "/deploy":
        f = create_task("deploy_cloudflare", title="Cloudflare 部署", source="telegram", user_text=arg)
        return f"已建立任務 <code>{f.name}</code>\n請在 Cursor 執行 deploy_to_cloudflare.ps1"
    if cmd == "/tasks":
        rows = list_tasks()
        if not rows:
            return "（無待辦任務）"
        lines = [f"• <code>{t['id']}</code> {t['kind']}" for t in rows[:15]]
        return "<b>待辦</b>\n" + "\n".join(lines)
    return "未知指令。/help"


def run_bot(*, poll_seconds: float = 2.0) -> None:
    load_dotenv()
    import os

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    allowed = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not allowed:
        raise SystemExit("請在 .env 設定 TELEGRAM_BOT_TOKEN 與 TELEGRAM_CHAT_ID")

    print(f"Hermes Telegram → Cursor 任務佇列（chat_id={allowed}）")
    print("Ctrl+C 結束\n")

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
                reply = handle_command(text)
            except Exception as exc:  # noqa: BLE001
                reply = f"失敗：<code>{exc}</code>"
            send_message(reply)
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
