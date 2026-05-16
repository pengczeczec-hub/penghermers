"""
Cloudflare Python Worker 實作（僅在 pywrangler / Workers 執行環境載入）。

本機請用：`uv run pywrangler dev`。
勿在一般 `python -c "import hermers.cf_worker"` 測試（需 Workers 執行期）。
"""

from __future__ import annotations

import json
from urllib.parse import urlparse

from workers import WorkerEntrypoint, Response

from hermers.worker_edge import scheduled_tick, worker_info


def _json(body: dict, *, status: int = 200) -> Response:
    return Response(
        json.dumps(body, ensure_ascii=False),
        status=status,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        url = urlparse(request.url)
        path = url.path or "/"

        if path in ("/", "/index.html"):
            body = (
                "<!DOCTYPE html><html lang=\"zh-Hant\"><head><meta charset=\"utf-8\"/>"
                "<title>Hermers Worker</title></head><body>"
                f"<h1>{worker_info()['title']}</h1>"
                "<p>Cloudflare Python Worker 已上線。API：<code>/api/health</code></p>"
                "</body></html>"
            )
            return Response(body, headers={"Content-Type": "text/html; charset=utf-8"})

        if path == "/api/health":
            return Response.json({"ok": True, **worker_info()})

        if path == "/api/trigger" and request.method == "POST":
            secret = getattr(self.env, "CRON_SECRET", None) or ""
            auth = request.headers.get("Authorization") or ""
            expected = f"Bearer {secret}".strip() if secret else ""
            if secret and auth != expected:
                return _json({"ok": False, "error": "unauthorized"}, status=401)
            result = await scheduled_tick(source="http", env=self.env)
            return Response.json({"ok": True, "result": result})

        if path == "/favicon.ico":
            return Response("", headers={"Content-Type": "image/x-icon"})

        return _json({"ok": False, "error": "not_found", "path": path}, status=404)

    async def scheduled(self, controller, env, ctx):
        cron = getattr(controller, "cron", "") or ""
        print(f"[Hermers] scheduled fired cron={cron!r}")
        result = await scheduled_tick(source=f"cron:{cron}", env=env)
        print(f"[Hermers] scheduled result={json.dumps(result, ensure_ascii=False)[:500]}")
