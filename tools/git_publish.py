"""
將 dist/ 與其他變更 add → commit → push。
需已設定 remote；認證請用 credential helper 或環境變數（勿把 token 寫進程式）。

用法:
  python tools/git_publish.py --message "chore: update digest"
  python tools/git_publish.py --dry-run
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], *, cwd: Path, dry_run: bool) -> None:
    print("+", " ".join(cmd))
    if dry_run:
        return
    proc = subprocess.run(cmd, cwd=cwd, check=False)
    if proc.returncode != 0:
        sys.exit(proc.returncode)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--message", "-m", default="chore: publish site", help="commit message")
    parser.add_argument("--dry-run", action="store_true", help="只列印將執行的 git 指令")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    dry = args.dry_run

    if (root / ".git").is_dir():
        run(["git", "add", "-A"], cwd=root, dry_run=dry)
        run(["git", "commit", "-m", args.message], cwd=root, dry_run=dry)
        run(["git", "push"], cwd=root, dry_run=dry)
    else:
        print("尚未初始化 git：請先在專案根目錄執行 git init 並設定 remote。", file=sys.stderr)
        sys.exit(1)

    tok = os.environ.get("GITHUB_TOKEN")
    if tok and not dry:
        # 提醒：勿將 token 印出；此處僅確認有設定（長度）
        print(f"GITHUB_TOKEN 已設定（長度 {len(tok)}）。")
    elif not dry:
        print("未偵測到 GITHUB_TOKEN；若 push 失敗，請用 gh auth login 或 credential manager。")


if __name__ == "__main__":
    main()
