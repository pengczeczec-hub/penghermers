"""
Cloudflare Python Worker 實作（僅在 pywrangler / Workers 執行環境載入）。
"""

from __future__ import annotations

import json
from urllib.parse import urlparse

from workers import WorkerEntrypoint, Response

from hermers.worker_edge import scheduled_tick, worker_info
from hermers.worker_static import load_home_or_fallback, read_dist_text, resolve_static_path


def _json(body: dict, *, status: int = 200) -> Response:
    return Response(
        json.dumps(body, ensure_ascii=False),
        status=status,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        parsed = urlparse(request.url)
        path = parsed.path or "/"
        url_str = str(request.url)

        # 首頁：dist/index.html，失敗則回傳預設剪報文章
        is_home = path in ("/", "/index.html") or url_str.rstrip("/").endswith(".dev")
        if is_home:
            loaded = load_home_or_fallback()
            if loaded:
                body, ctype = loaded
                return Response(body, headers={"Content-Type": ctype})
            return Response(
                "<h1>Hermers</h1><p>dist/index.html 尚未產生，請在本機執行 pipeline。</p>",
                headers={"Content-Type": "text/html; charset=utf-8"},
            )

        # 其他靜態檔：/posts/*.html 等
        static_rel = resolve_static_path(path)
        if static_rel:
            loaded = read_dist_text(static_rel)
            if loaded:
                body, ctype = loaded
                return Response(body, headers={"Content-Type": ctype})

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
