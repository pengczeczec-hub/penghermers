"""
驗證 GITHUB_TOKEN 並可選推送到 config/hermes.yaml 指定倉庫。

用法:
  python tools/test_github_push.py
  python tools/test_github_push.py --dry-run
  python tools/test_github_push.py --push
"""

from __future__ import annotations

import argparse
import sys

from hermers.env_load import load_dotenv
from hermers.hermes_config import load_hermes_config
from hermers.shell_runner import ensure_git_remote, git_push, verify_github_token


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="只列印將執行的 git 步驟")
    parser.add_argument("--push", action="store_true", help="實際 push 到 hermes.yaml 的 repo")
    args = parser.parse_args()

    cfg = load_hermes_config()
    print("=== Hermes GitHub Token 測試 ===\n")
    print(f"目標倉庫: {cfg.github_repo_url}")
    print(f"分支:     {cfg.github_branch}\n")

    info = verify_github_token()
    if not info.get("ok"):
        print(f"FAIL: {info.get('error')}")
        if info.get("hint"):
            print(f"提示: {info.get('hint')}")
        sys.exit(1)
    print(f"OK: GitHub 認證有效，login={info.get('login')}（來源: {info.get('source')}）\n")

    remote = ensure_git_remote(cfg)
    print(f"OK: git remote '{remote}' → {cfg.github_repo_url}\n")

    if not args.push and not args.dry_run:
        print("通過。若要試推送請加 --dry-run 或 --push")
        return

    try:
        git_push(dry_run=args.dry_run and not args.push, message="chore: hermes test push", cfg=cfg)
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {exc}")
        sys.exit(1)

    if args.dry_run and not args.push:
        print("\nOK: dry-run 完成")
    else:
        print("\nOK: 已推送到", cfg.github_repo_url)


if __name__ == "__main__":
    main()
