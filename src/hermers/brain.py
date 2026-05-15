"""
Hermers「大腦」接點：在 Cursor 外也可被 CLI / CI 呼叫的薄層。

複雜推理與內容生成預設在 Cursor Agent 內完成；此模組負責
一致的路徑、版本資訊與之後可掛載的管線步驟。
"""

from __future__ import annotations

import argparse

from hermers import __version__
from hermers.paths import dist_dir, pending_dir, posts_dir, repo_root
from hermers.telegram_notify import status_text as telegram_status


def status_text() -> str:
    root = repo_root()
    d = dist_dir()
    index = d / "index.html"
    pending = len(list(pending_dir().glob("*/meta.json"))) if pending_dir().is_dir() else 0
    published = len(list(posts_dir().glob("*.html"))) if posts_dir().is_dir() else 0
    return (
        f"Hermers {__version__}\n"
        f"  repo_root: {root}\n"
        f"  dist:      {d} ({'ok' if index.is_file() else 'missing index.html'})\n"
        f"  pending:   {pending} 則待審（staging/pending/）\n"
        f"  published: {published} 則已通過（dist/posts/）\n"
        f"  {telegram_status()}\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Hermers brain stub / health check")
    parser.add_argument("--version", action="store_true", help="print version and exit")
    args = parser.parse_args()
    if args.version:
        print(__version__)
        return
    print(status_text(), end="")


if __name__ == "__main__":
    main()
