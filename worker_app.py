"""
Cloudflare Worker 入口（main.py 轉匯）。

靜態剪報由 wrangler [assets] directory=dist 提供；本 Worker 處理 /api/*，
其餘路徑轉交 env.ASSETS.fetch(request)。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from workers import WorkerEntrypoint, Response

from worker_dispatch import scheduled_tick

_DIST = Path(__file__).resolve().parent / "dist"
_FALLBACK_POST = "posts/20260516-nyt-and-vaping-how-to-lie-by-saying-only.html"


def worker_info() -> dict[str, Any]:
    return {
        "title": "Hermers",
        "runtime": "cloudflare-python-worker",
        "role": "edge_static_and_api",
    }


def _json(body: dict, *, status: int = 200) -> Response:
    return Response(
        json.dumps(body, ensure_ascii=False),
        status=status,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )


def _content_type(path: Path) -> str:
    return {
        ".html": "text/html; charset=utf-8",
        ".json": "application/json; charset=utf-8",
    }.get(path.suffix.lower(), "application/octet-stream")


def _safe_file(rel: str) -> Path | None:
    root = _DIST.resolve()
    if not root.is_dir():
        return None
    target = (root / rel.lstrip("/")).resolve()
    if not str(target).startswith(str(root)):
        return None
    return target if target.is_file() else None


def _read_dist(rel: str) -> tuple[str, str] | None:
    path = _safe_file(rel)
    if path is None:
        return None
    return path.read_text(encoding="utf-8"), _content_type(path)


def _local_static_response(path: str) -> Response | None:
    """本機 pywrangler dev：從 dist/ 讀檔（雲端請用 ASSETS）。"""
    rel = "index.html" if path in ("/", "/index.html") else path.lstrip("/")
    if path in ("/", "/index.html"):
        loaded = _read_dist("index.html") or _read_dist(_FALLBACK_POST)
    else:
        loaded = _read_dist(rel)
    if not loaded:
        return None
    body, ctype = loaded
    return Response(body, headers={"Content-Type": ctype})


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        parsed = urlparse(request.url)
        path = parsed.path or "/"

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

        assets = getattr(self.env, "ASSETS", None)
        if assets is not None:
            return await assets.fetch(request)

        local = _local_static_response(path)
        if local is not None:
            return local

        return _json({"ok": False, "error": "not_found", "path": path}, status=404)

    async def scheduled(self, controller, env, ctx):
        cron = getattr(controller, "cron", "") or ""
        print(f"[Hermers] scheduled cron={cron!r}")
        result = await scheduled_tick(source=f"cron:{cron}", env=env)
        print(json.dumps(result, ensure_ascii=False)[:500])
