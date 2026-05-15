from __future__ import annotations

import json

from hermers.paths import data_dir, seen_urls_path


def load_seen() -> set[str]:
    path = seen_urls_path()
    if not path.is_file():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return set(data.get("urls") or [])


def save_seen(urls: set[str]) -> None:
    data_dir().mkdir(parents=True, exist_ok=True)
    seen_urls_path().write_text(
        json.dumps({"urls": sorted(urls)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def remember(urls: set[str], new_url: str) -> None:
    urls.add(new_url)
    save_seen(urls)
