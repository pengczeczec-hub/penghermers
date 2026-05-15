from __future__ import annotations

import argparse
import re
import shutil
from datetime import datetime, timezone

from hermers.config_load import load_config
from hermers.discover import discover_domain
from hermers.draft import write_pending
from hermers.fetch import fetch_article
from hermers.paths import pending_dir, staging_dir
from hermers.seen import load_seen, remember
from hermers.site import write_review_page
from hermers.telegram_notify import notify_pipeline_done


def _slug(text: str, max_len: int = 40) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "-", text, flags=re.UNICODE).strip("-").lower()
    return (s[:max_len] or "post").strip("-")


def run_pipeline(*, dry_run: bool = False) -> int:
    cfg = load_config()
    seen = load_seen()
    pending_dir().mkdir(parents=True, exist_ok=True)
    staging_dir().mkdir(parents=True, exist_ok=True)

    candidates = []
    per_domain = max(2, cfg.max_items // max(len(cfg.domains), 1))
    for domain in cfg.domains:
        found = discover_domain(domain, limit=per_domain)
        for item in found:
            if item.url in seen:
                continue
            candidates.append(item)

    candidates = candidates[: cfg.max_items]
    if not candidates:
        print("沒有新的熱門項目（可能已全部處理過）。可編輯 data/seen_urls.json 清除舊紀錄。")
        write_review_page()
        if notify_pipeline_done(created=0, dry_run=dry_run):
            print("已發送 Telegram 通知。")
        return 0

    created = 0
    for item in candidates:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        draft_id = f"{stamp}-{_slug(item.title)}"
        folder = pending_dir() / draft_id
        if folder.exists():
            continue

        print(f"[{'dry-run' if dry_run else 'fetch'}] {item.title[:60]}…")
        print(f"         {item.url}")
        if dry_run:
            created += 1
            continue

        try:
            extract = fetch_article(item.url)
        except Exception as exc:  # noqa: BLE001 — 單則失敗不阻斷整批
            print(f"  略過（擷取失敗）: {exc}")
            continue

        write_pending(folder, item=item, extract=extract, draft_id=draft_id)
        remember(seen, item.url)
        created += 1

    review = write_review_page()
    print(f"\n完成：新增 {created} 則待審草稿。")
    print(f"請開啟審核頁：{review}")
    if notify_pipeline_done(created=created, dry_run=dry_run):
        print("已發送 Telegram 通知（待審）。")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Hermers：從 RSS 發現熱門 → 擷取 → 待審草稿")
    parser.add_argument("--dry-run", action="store_true", help="只列出將處理的連結，不擷取")
    args = parser.parse_args()
    raise SystemExit(run_pipeline(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
