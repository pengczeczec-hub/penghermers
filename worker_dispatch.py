"""
Cloudflare Worker 與本機共用的排程觸發邏輯（放在倉庫根目錄，便於 pywrangler 打包；勿 import hermers.*）。
"""

from __future__ import annotations

from typing import Any


async def scheduled_tick(*, source: str, env: object | None = None) -> dict[str, Any]:
    """
    排程或 POST /api/trigger 時執行。

    優先序：
    1) `GITHUB_REPOSITORY` + `GITHUB_DISPATCH_TOKEN`：GitHub repository_dispatch
       觸發 `hermers-digest`。
    2) `PIPELINE_WEBHOOK_URL`：對自訂 URL 送 POST（相容舊設定）。
    """
    repo = _env_str(env, "GITHUB_REPOSITORY")
    token = _env_str(env, "GITHUB_DISPATCH_TOKEN")
    if repo and token:
        return await _github_repository_dispatch(
            repo=repo, token=token, source=source
        )

    if repo and not token:
        return {
            "source": source,
            "github_dispatch_pending": True,
            "hint": "已設定 GITHUB_REPOSITORY；請以 Worker Secret 設定 GITHUB_DISPATCH_TOKEN（"
            "classic PAT，含 repo），或使用 PIPELINE_WEBHOOK_URL。",
        }

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
        "hint": "請在 Worker 設定 GITHUB_REPOSITORY + GITHUB_DISPATCH_TOKEN（建議），"
        "或設定 PIPELINE_WEBHOOK_URL。",
    }


async def _github_repository_dispatch(
    *, repo: str, token: str, source: str
) -> dict[str, Any]:
    url = f"https://api.github.com/repos/{repo}/dispatches"
    payload = {
        "event_type": "hermers-digest",
        "client_payload": {"source": source},
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        import httpx

        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(url, json=payload, headers=headers)
            body_preview = (r.text or "")[:300]
            return {
                "source": source,
                "github_dispatch_status": r.status_code,
                "github_dispatch_ok": r.is_success,
                "github_dispatch_body_preview": body_preview if not r.is_success else "",
            }
    except Exception as exc:  # noqa: BLE001
        return {"source": source, "github_dispatch_error": str(exc)}


def _env_str(env: object | None, key: str) -> str:
    if env is None:
        return ""
    raw = getattr(env, key, None)
    if raw is None:
        return ""
    return str(raw).strip()


__all__ = ["scheduled_tick"]
