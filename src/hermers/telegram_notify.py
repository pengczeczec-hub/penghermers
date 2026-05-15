from __future__ import annotations

import json
import os

import httpx

from hermers.env_load import load_dotenv
from hermers.paths import pending_dir, repo_root


def _enabled() -> bool:
    load_dotenv()
    flag = os.environ.get("TELEGRAM_NOTIFY", "1").strip().lower()
    if flag in ("0", "false", "no", "off"):
        return False
    return bool(os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"))


def is_configured() -> bool:
    load_dotenv()
    return bool(os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"))


def send_message(text: str, *, disable_preview: bool = True) -> bool:
    load_dotenv()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text[:4000],
        "disable_web_page_preview": disable_preview,
    }
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
    return bool(data.get("ok"))


def _pending_lines(limit: int = 8) -> list[str]:
    lines: list[str] = []
    if not pending_dir().is_dir():
        return lines
    for meta_path in sorted(pending_dir().glob("*/meta.json"))[:limit]:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        draft_id = meta.get("id", meta_path.parent.name)
        title = (meta.get("title") or "")[:50]
        lines.append(f"• <code>{draft_id}</code>\n  {title}")
    return lines


def notify_pipeline_done(*, created: int, dry_run: bool = False) -> bool:
    if not _enabled():
        return False
    review = repo_root() / "staging" / "review.html"
    site = os.environ.get("SITE_PUBLIC_URL", "").strip()
    lines = [
        "<b>Hermers</b>",
        f"管線完成：新增 <b>{created}</b> 則待審" + ("（dry-run）" if dry_run else ""),
        "",
        f"本機審核頁：\n<code>{review}</code>",
    ]
    if site:
        lines.append(f"\n網站：{site}")
    pending = _pending_lines()
    if pending:
        lines.append("\n<b>待審 ID（approve.bat）：</b>")
        lines.extend(pending)
    lines.append("\n通過後請在本機執行 <code>publish.bat</code> 才會上 GitHub。")
    return send_message("\n".join(lines))


def notify_review_action(*, action: str, draft_id: str, title: str = "") -> bool:
    if not _enabled():
        return False
    title_line = f"\n{title[:80]}" if title else ""
    extra = (
        "\n請執行 <code>publish.bat</code> 推送到 GitHub。"
        if action == "通過審核"
        else ""
    )
    text = f"<b>Hermers</b>\n已<b>{action}</b>：<code>{draft_id}</code>{title_line}{extra}"
    return send_message(text)


def status_text() -> str:
    load_dotenv()
    if is_configured():
        return "Telegram：已設定（TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID）"
    if os.environ.get("TELEGRAM_BOT_TOKEN", "").strip():
        return "Telegram：僅有 TOKEN，尚缺 TELEGRAM_CHAT_ID（執行 telegram-chat-id.bat）"
    return "Telegram：未設定（請編輯 .env，並執行 telegram-test.bat）"


def discover_chat_ids() -> list[dict]:
    """呼叫 getUpdates；需先對 Bot 按 Start 並傳一則訊息。"""
    load_dotenv()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise ValueError("請先在 .env 設定 TELEGRAM_BOT_TOKEN")

    if ":" not in token or len(token) < 20:
        raise ValueError(
            "TOKEN 格式似乎不對。應來自 @BotFather，形如 123456789:AAHxxxxxxxx"
        )

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(url)
        if resp.status_code == 404:
            raise ValueError(
                "Telegram 回傳 404：TOKEN 無效或網址錯誤。"
                "請確認 .env 的 token 完整、無空格、不是 Bot 使用者名稱。"
            )
        resp.raise_for_status()
        data = resp.json()

    if not data.get("ok"):
        desc = data.get("description", "unknown")
        raise ValueError(f"Telegram API 錯誤：{desc}")

    seen: dict[int, dict] = {}
    for item in data.get("result") or []:
        msg = item.get("message") or item.get("edited_message") or {}
        chat = msg.get("chat") or {}
        cid = chat.get("id")
        if cid is None:
            continue
        seen[int(cid)] = {
            "id": cid,
            "type": chat.get("type", ""),
            "title": chat.get("title") or chat.get("username") or chat.get("first_name") or "",
        }
    return list(seen.values())
