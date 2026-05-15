#!/usr/bin/env python3
"""
Hermes 編排介面：不呼叫外部 AI API。
產生任務與 CURSOR_SPEC.md 供 Cursor Agent 執行；系統操作用本機終端機。
"""

from __future__ import annotations

import argparse
import sys

from hermers.cursor_tasks import complete_task, create_task, list_tasks
from hermers.hermes_config import load_hermes_config
from hermers.paths import repo_root
from hermers.shell_runner import verify_github_token


def cmd_status() -> int:
    cfg = load_hermes_config()
    pending = list_tasks(cfg, pending_only=True)
    done = list_tasks(cfg, pending_only=False)
    gh = verify_github_token()
    print(f"Hermes @ {repo_root()}")
    print(f"  Cursor 任務（待辦）: {len(pending)}")
    print(f"  Cursor 任務（完成）: {len(done)}")
    if gh.get("ok"):
        print(f"  GITHUB_TOKEN: 有效（{gh.get('login')}）")
    else:
        print(f"  GITHUB_TOKEN: {gh.get('error')}")
    print(f"  部署目標: {cfg.github_repo_url}")
    print("\n在 Cursor 處理 tasks/pending/*/CURSOR_SPEC.md")
    return 0


def cmd_task_new(args: argparse.Namespace) -> int:
    folder = create_task(
        args.kind,
        title=args.title or args.kind,
        source="cli",
        user_text=args.text or "",
    )
    print(f"已建立任務：{folder.name}")
    print(f"  → {folder / 'CURSOR_SPEC.md'}")
    return 0


def cmd_task_list() -> int:
    rows = list_tasks()
    if not rows:
        print("（無待辦任務）")
        return 0
    for t in rows:
        print(f"{t['id']}\t{t['kind']}\t{t['title']}")
    return 0


def cmd_complete(args: argparse.Namespace) -> int:
    dest = complete_task(args.task_id)
    print(f"已完成：{dest}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Hermes 編排（Cursor 為唯一 AI 引擎）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="狀態")

    p_task = sub.add_parser("task", help="任務")
    task_sub = p_task.add_subparsers(dest="task_cmd", required=True)
    p_new = task_sub.add_parser("new", help="建立 Cursor 任務")
    p_new.add_argument("--kind", "-k", default="user_request")
    p_new.add_argument("--title", "-t", required=True)
    p_new.add_argument("--text", default="")
    task_sub.add_parser("list", help="列出待辦")

    p_done = sub.add_parser("complete", help="標記任務完成")
    p_done.add_argument("task_id")

    p_gh = sub.add_parser("test-github", help="測試 token / 推送")
    p_gh.add_argument("--dry-run", action="store_true")
    p_gh.add_argument("--push", action="store_true")

    args = parser.parse_args()
    if args.cmd == "status":
        raise SystemExit(cmd_status())
    if args.cmd == "task" and args.task_cmd == "new":
        raise SystemExit(cmd_task_new(args))
    if args.cmd == "task" and args.task_cmd == "list":
        raise SystemExit(cmd_task_list())
    if args.cmd == "complete":
        raise SystemExit(cmd_complete(args))
    if args.cmd == "test-github":
        import subprocess

        cmd = [sys.executable, str(repo_root() / "tools" / "test_github_push.py")]
        if args.dry_run:
            cmd.append("--dry-run")
        if args.push:
            cmd.append("--push")
        raise SystemExit(subprocess.run(cmd, cwd=repo_root()).returncode)


if __name__ == "__main__":
    main()
