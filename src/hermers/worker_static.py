"""
從 dist/ 讀取剪報靜態檔（本機與 Worker 部署包內路徑）。
"""

from __future__ import annotations

from pathlib import Path

FALLBACK_POST = "posts/20260516-nyt-and-vaping-how-to-lie-by-saying-only.html"


def dist_root() -> Path:
    return Path(__file__).resolve().parents[2] / "dist"


def _content_type(path: Path) -> str:
    return {
        ".html": "text/html; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
    }.get(path.suffix.lower(), "application/octet-stream")


def _safe_file(rel: str) -> Path | None:
    root = dist_root().resolve()
    target = (root / rel.lstrip("/")).resolve()
    if not str(target).startswith(str(root)):
        return None
    return target if target.is_file() else None


def read_dist_text(rel: str) -> tuple[str, str] | None:
    path = _safe_file(rel)
    if path is None:
        return None
    return path.read_text(encoding="utf-8"), _content_type(path)


def resolve_static_path(url_path: str) -> str | None:
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


def load_home_or_fallback() -> tuple[str, str] | None:
    hit = read_dist_text("index.html")
    if hit:
        return hit
    return read_dist_text(FALLBACK_POST)
