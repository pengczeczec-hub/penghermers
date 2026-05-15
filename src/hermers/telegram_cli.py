from __future__ import annotations

import argparse
import os

from hermers.env_load import load_dotenv
from hermers.telegram_notify import discover_chat_ids, is_configured, send_message, status_text


def main() -> None:
    parser = argparse.ArgumentParser(description="Hermers Telegram 通知")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="顯示是否已設定")
    sub.add_parser("discover", help="從 getUpdates 列出 Chat ID（需先對 Bot 傳訊息）")

    p_test = sub.add_parser("test", help="發送測試訊息")
    p_test.add_argument("--message", "-m", default="Hermers：Telegram 連線測試成功。")

    args = parser.parse_args()
    if args.cmd == "status":
        print(status_text())
        load_dotenv()
        has_token = bool(os.environ.get("TELEGRAM_BOT_TOKEN", "").strip())
        raise SystemExit(0 if is_configured() else (0 if has_token else 1))

    if args.cmd == "discover":
        try:
            chats = discover_chat_ids()
        except ValueError as exc:
            print(exc)
            print("\n請確認：")
            print("  1. .env 內 TELEGRAM_BOT_TOKEN= 來自 @BotFather 的整串（含冒號）")
            print("  2. 已在 Telegram 對您的 Bot 按 Start 並傳送「hi」")
            raise SystemExit(1) from exc
        if not chats:
            print("沒有收到任何訊息。")
            print("請先對 Bot 按 Start 並傳一則訊息，再執行一次。")
            raise SystemExit(1)
        print("找到以下 Chat ID，請擇一填入 .env 的 TELEGRAM_CHAT_ID：\n")
        for c in chats:
            print(f"  TELEGRAM_CHAT_ID={c['id']}  ({c['type']}: {c['title']})")
        raise SystemExit(0)

    if not is_configured():
        print("未設定完整 Telegram。請複製 .env.example 為 .env 並填入：")
        print("  TELEGRAM_BOT_TOKEN=（來自 @BotFather）")
        print("  TELEGRAM_CHAT_ID=（執行 telegram-chat-id.bat 查詢）")
        raise SystemExit(1)

    ok = send_message(f"<b>{args.message}</b>")
    if ok:
        print("已發送測試訊息到 Telegram。")
        raise SystemExit(0)
    print("發送失敗。")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
