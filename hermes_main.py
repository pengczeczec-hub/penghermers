#!/usr/bin/env python3
"""
Hermes 主入口：主動執行（非任務提醒器）。
Telegram Bot 與 CLI 皆呼叫此模組。
"""

from __future__ import annotations

import argparse
import os
import re
import sys

from hermers.env_load import load_dotenv
from hermers.executor import HermesExecutor

load_dotenv()
# 若 .env 未設 SITE_PUBLIC_URL，使用已上線的 Workers 網址（.env 可覆寫）
os.environ.setdefault(
    "SITE_PUBLIC_URL",
    "https://penghermers.pengczeczec.workers.dev",
)


def _extract_urls(text: str) -> list[str]:
    return re.findall(r"https?://\S+", text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hermes 主動執行器")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("status")
    p_pipe = sub.add_parser("pipeline")
    p_pipe.add_argument("--push", action="store_true", help="完成後推送 GitHub")
    p_pipe.add_argument("--deploy", action="store_true", help="完成後 deploy（含 git push 與 Cloudflare）")
    sub.add_parser("publish")
    sub.add_parser("deploy")
    p_url = sub.add_parser("url")
    p_url.add_argument("link")
    p_agent = sub.add_parser("agent")
    p_agent.add_argument("message", nargs="+")

    args = parser.parse_args(argv)
    ex = HermesExecutor()

    if not args.cmd:
        r = ex.status()
        print(r.message)
        return 0 if r.ok else 1

    if args.cmd == "status":
        r = ex.status()
    elif args.cmd == "pipeline":
        r = ex.run_pipeline(
            push=bool(getattr(args, "push", False)),
            deploy=bool(getattr(args, "deploy", False)),
        )
    elif args.cmd == "publish":
        r = ex.publish()
    elif args.cmd == "deploy":
        r = ex.deploy()
    elif args.cmd == "url":
        r = ex.ingest_url(args.link, push=False)
    elif args.cmd == "agent":
        from hermers.agent.runner import AgentRunner

        r = AgentRunner().handle(" ".join(args.message))
    else:
        print("未知指令")
        return 1

    print(r.message.replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", ""))
    return 0 if r.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
