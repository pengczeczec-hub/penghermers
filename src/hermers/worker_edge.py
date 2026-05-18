"""
可在 Cloudflare Python Worker 內安全載入的邊緣邏輯。

禁止在此模組 import：pipeline、executor、paths.repo_root 等依賴本機倉庫路徑的程式。
剪報本體請在本機 / CI 執行 hermers-pipeline；排程觸發實作於倉庫根目錄 `worker_dispatch.py`。
"""

from __future__ import annotations

from typing import Any

from worker_dispatch import scheduled_tick


def worker_info() -> dict[str, Any]:
    return {
        "title": "Hermers",
        "runtime": "cloudflare-python-worker",
        "role": "edge_api_and_cron",
    }


__all__ = ["scheduled_tick", "worker_info"]
