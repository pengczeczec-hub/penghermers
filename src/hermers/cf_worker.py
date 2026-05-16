"""本機相容層；Cloudflare 實際入口為根目錄 worker_app.py。"""

from worker_app import Default

__all__ = ["Default"]
