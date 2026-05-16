"""
Wrangler 入口：Cloudflare 只打包此檔與其 import 鏈（見 worker_app.py）。
"""

from worker_app import Default

__all__ = ["Default"]
