"""首頁：一週篩選、精選 Top 5、日期瀏覽（供 site.rebuild_index 使用）。"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any

from hermers.discover import FeedItem
from hermers.ranking import market_impact_score

HOME_WEEK_DAYS = 7
HOME_ARCHIVE_DAYS = 90


def entry_calendar_date(meta: dict[str, Any], slug: str) -> date | None:
    for key in ("approved_at", "created_at"):
        raw = meta.get(key)
        if not raw:
            continue
        try:
            return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).date()
        except ValueError:
            continue
    m = re.match(r"^(\d{8})", slug)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y%m%d").date()
        except ValueError:
            return None
    return None


def importance_for_entry(meta: dict[str, Any], *, title: str, slug: str) -> float:
    stored = meta.get("importance_score")
    if stored is not None:
        try:
            return float(stored)
        except (TypeError, ValueError):
            pass
    published: datetime | None = None
    for key in ("approved_at", "created_at"):
        raw = meta.get(key)
        if raw:
            try:
                published = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                break
            except ValueError:
                continue
    item = FeedItem(
        domain_id=str(meta.get("domain_id") or "manual"),
        domain_name=str(meta.get("domain_name") or ""),
        title=title,
        url=str(meta.get("url") or slug),
        published=published,
        source=str(meta.get("rss_source") or ""),
        section_zh=str(meta.get("section_zh") or ""),
        section_en=str(meta.get("section_en") or ""),
    )
    return market_impact_score(item)


def week_start(today: date | None = None) -> date:
    today = today or datetime.now(timezone.utc).date()
    return today - timedelta(days=HOME_WEEK_DAYS - 1)


def in_current_week(d: date | None, today: date | None = None) -> bool:
    if d is None:
        return False
    today = today or datetime.now(timezone.utc).date()
    return week_start(today) <= d <= today


def in_archive_window(d: date | None, today: date | None = None) -> bool:
    if d is None:
        return False
    today = today or datetime.now(timezone.utc).date()
    return d >= today - timedelta(days=HOME_ARCHIVE_DAYS - 1)


def pick_weekly_top5(entries: list[dict[str, Any]], *, today: date | None = None) -> list[dict[str, Any]]:
    today = today or datetime.now(timezone.utc).date()
    week_rows = [e for e in entries if in_current_week(e.get("post_date"), today)]
    week_rows.sort(
        key=lambda e: (
            float(e.get("importance") or 0),
            e.get("published") or "",
        ),
        reverse=True,
    )
    seen: set[str] = set()
    top: list[dict[str, Any]] = []
    for row in week_rows:
        href = row.get("href") or ""
        if href in seen:
            continue
        seen.add(href)
        top.append(row)
        if len(top) >= 5:
            break
    return top


def enrich_entry(row: dict[str, Any], meta: dict[str, Any], slug: str) -> dict[str, Any]:
    title = str(row.get("title") or slug)
    post_date = entry_calendar_date(meta, slug)
    importance = importance_for_entry(meta, title=title, slug=slug)
    out = dict(row)
    out["post_date"] = post_date
    out["post_date_iso"] = post_date.isoformat() if post_date else ""
    out["importance"] = importance
    out["in_week"] = in_current_week(post_date)
    return out
