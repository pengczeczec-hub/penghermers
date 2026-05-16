"""
Cloudflare Worker 入口邏輯（與 main.py 同目錄，供 pywrangler 打包）。

勿 import hermers.*（src 套件不會自動進 Worker）；本機 Telegram / pipeline 仍用 hermers。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from workers import WorkerEntrypoint, Response

_DIST = Path(__file__).resolve().parent / "dist"
_FALLBACK_POST = "posts/20260516-nyt-and-vaping-how-to-lie-by-saying-only.html"


def worker_info() -> dict[str, Any]:
    return {
        "title": "Hermers",
        "runtime": "cloudflare-python-worker",
        "role": "edge_static_and_api",
    }


async def scheduled_tick(*, source: str, env: object | None = None) -> dict[str, Any]:
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
        "hint": "未設定 PIPELINE_WEBHOOK_URL",
    }


def _env_str(env: object | None, key: str) -> str:
    if env is None:
        return ""
    raw = getattr(env, key, None)
    if raw is None:
        return ""
    return str(raw).strip()


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


def _resolve_static(url_path: str) -> str | None:
    path = url_path or "/"
    if path in ("/", "/index.html"):
        return "index.html"
    if path.startswith("/posts/"):
        rel = path.lstrip("/")
        if rel.endswith((".html", ".json")):
            return rel
        return f"{rel}.html"
    if path.startswith("/") and "." in Path(path).name:
        return path.lstrip("/")
    return None


def _load_home() -> tuple[str, str] | None:
    hit = _read_dist("index.html")
    if hit:
        return hit
    return _read_dist(_FALLBACK_POST)


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

        is_home = path in ("/", "/index.html") or url_str.rstrip("/").endswith(".dev")
        if is_home:
            loaded = _load_home()
            if loaded:
                body, ctype = loaded
                return Response(body, headers={"Content-Type": ctype})
            return Response(
                "<h1>Hermers</h1><p>dist/index.html 尚未產生。</p>",
                headers={"Content-Type": "text/html; charset=utf-8"},
            )

        static_rel = _resolve_static(path)
        if static_rel:
            loaded = _read_dist(static_rel)
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
        print(f"[Hermers] scheduled cron={cron!r}")
        result = await scheduled_tick(source=f"cron:{cron}", env=env)
        print(json.dumps(result, ensure_ascii=False)[:500])
