"""哪些 URL 不應被當成外部新聞 ingest。"""

from __future__ import annotations

import os

from hermers.env_load import load_dotenv


def is_own_site_url(url: str) -> bool:
    u = (url or "").strip().rstrip(".,)").lower()
    if not u:
        return False
    if "penghermers" in u and "workers.dev" in u:
        return True
    if "github.com" in u and "penghermers" in u:
        return True
    if "/staging/" in u or "review.html" in u:
        return True
    load_dotenv()
    site = os.environ.get("SITE_PUBLIC_URL", "").strip().rstrip("/").lower()
    if site and (u == site or u.startswith(site + "/")):
        return True
    return False
