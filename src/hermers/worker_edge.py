"""
可在 Cloudflare Python Worker 內安全載入的邊緣邏輯。

禁止在此模組 import：pipeline、executor、paths.repo_root 等依賴本機倉庫路徑的程式。
剪報本體請在本機 / CI 執行 hermers-pipeline；Worker 排程可改為呼叫 GitHub API 觸發 workflow。
"""

from __future__ import annotations

from typing import Any


def worker_info() -> dict[str, Any]:
    return {
        "title": "Hermers",
        "runtime": "cloudflare-python-worker",
        "role": "edge_api_and_cron",
    }


async def scheduled_tick(*, source: str, env: object | None = None) -> dict[str, Any]:
    """
    排程或 POST /api/trigger 時執行。請在此改寫為實際業務（例如 httpx 呼叫 Actions webhook）。
    """
    webhook = _env_str(env, "PIPELINE_WEBHOOK_URL")
    if webhook:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(webhook)
                return {
                    "source": source,
                    "webhook_status": r.status_code,
                    "webhook_ok": r.is_success,
                }
        except Exception as exc:  # noqa: BLE001
            return {"source": source, "webhook_error": str(exc)}

    return {
        "source": source,
        "hint": "未設定 PIPELINE_WEBHOOK_URL：請在 Worker 環境變數或 wrangler secrets 設定，"
        "或於此函式改寫為 D1/R2/Queues 等邊緣邏輯。",
    }


def _env_str(env: object | None, key: str) -> str:
    if env is None:
        return ""
    raw = getattr(env, key, None)
    if raw is None:
        return ""
    return str(raw).strip()
