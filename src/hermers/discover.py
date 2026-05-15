from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from time import mktime

import feedparser

from hermers.config_load import DomainConfig


@dataclass
class FeedItem:
    domain_id: str
    domain_name: str
    title: str
    url: str
    published: datetime | None
    source: str


def _parse_date(entry: feedparser.FeedParserDict) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    return datetime.fromtimestamp(mktime(parsed), tz=timezone.utc)


def _matches_keywords(title: str, keywords: list[str]) -> bool:
    if not keywords:
        return True
    lower = title.lower()
    return any(k.lower() in lower for k in keywords)


def discover_domain(domain: DomainConfig, *, limit: int) -> list[FeedItem]:
    items: list[FeedItem] = []
    for feed_url in domain.rss:
        parsed = feedparser.parse(feed_url)
        source = parsed.feed.get("title") or feed_url
        for entry in parsed.entries[: limit * 2]:
            title = (entry.get("title") or "").strip()
            url = (entry.get("link") or "").strip()
            if not title or not url:
                continue
            if not _matches_keywords(title, domain.keywords):
                continue
            items.append(
                FeedItem(
                    domain_id=domain.id,
                    domain_name=domain.name,
                    title=title,
                    url=url,
                    published=_parse_date(entry),
                    source=source,
                )
            )
    items.sort(key=lambda x: x.published or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return items[:limit]
