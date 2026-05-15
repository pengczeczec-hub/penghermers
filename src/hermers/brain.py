"""
Hermers「大腦」接點：在 Cursor 外也可被 CLI / CI 呼叫的薄層。

複雜推理與內容生成預設在 Cursor Agent 內完成；此模組負責
一致的路徑、版本資訊與之後可掛載的管線步驟。
"""

from __future__ import annotations

import argparse
from pathlib import Path

from hermers import __version__


def repo_root() -> Path:
    """專案根目錄（假設從倉庫根執行，以目前檔案位置向上推算）。"""
    return Path(__file__).resolve().parents[2]


def dist_dir() -> Path:
    return repo_root() / "dist"


def status_text() -> str:
    root = repo_root()
    d = dist_dir()
    index = d / "index.html"
    return (
        f"Hermers {__version__}\n"
        f"  repo_root: {root}\n"
        f"  dist:      {d} ({'ok' if index.is_file() else 'missing index.html'})\n"
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
