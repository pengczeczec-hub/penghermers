"""
Wrangler 入口模組：實作於 hermers.cf_worker。

剪報完整管線（RSS → 寫入 staging/dist）依賴本機檔案系統；邊緣整合見 docs/CLOUDFLARE_WORKER.md。
"""

from hermers.cf_worker import Default

__all__ = ["Default"]
