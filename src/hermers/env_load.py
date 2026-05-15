from __future__ import annotations

import os
from pathlib import Path

from hermers.paths import repo_root


def load_dotenv() -> None:
    """讀取專案根目錄 .env（不覆蓋已存在的環境變數）。"""
    path = repo_root() / ".env"
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
