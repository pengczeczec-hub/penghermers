from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx

from hermers.config_load import DomainConfig


@dataclass
class FeedItem:
    domain_id: str
    domain_name: str
    title: str
    url: str
    published: datetime | None
    source: str
    section_zh: str | None = None
    section_en: str | None = None


def _parse_date_text(text: str | None) -> datetime | None:
    if not text:
        return None
    text = text.strip()
    try:
        return parsedate_to_datetime(text).astimezone(timezone.utc)
    except (TypeError, ValueError):
        pass
    try:
        iso = text.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def _local_tag(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _child_text(node: ET.Element, names: tuple[str, ...]) -> str:
    for child in node:
        if _local_tag(child.tag) in names:
            if child.text:
                return child.text.strip()
            if child.attrib.get("href"):
                return child.attrib["href"].strip()
    return ""


def _entry_published(node: ET.Element) -> datetime | None:
    for name in ("pubDate", "published", "updated", "date"):
        for child in node:
            if _local_tag(child.tag) == name:
                parsed = _parse_date_text(child.text)
                if parsed:
                    return parsed
    return None


def _feed_nodes(root: ET.Element) -> list[ET.Element]:
    for tag in ("item", "entry"):
        nodes = [el for el in root.iter() if _local_tag(el.tag) == tag]
        if nodes:
            return nodes
    return []


def _feed_source_title(root: ET.Element, fallback: str) -> str:
    for container in ("channel", "feed"):
        for el in root.iter():
            if _local_tag(el.tag) != container:
                continue
            for child in el:
                if _local_tag(child.tag) == "title" and child.text:
                    return child.text.strip()
    for el in root.iter():
        if _local_tag(el.tag) == "title" and el.text:
            return el.text.strip()
    return fallback


def _matches_keywords(title: str, keywords: list[str]) -> bool:
    if not keywords:
        return True
    lower = title.lower()
    return any(k.lower() in lower for k in keywords)


def discover_domain(domain: DomainConfig, *, limit: int) -> list[FeedItem]:
    items: list[FeedItem] = []
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        for feed_url in domain.rss:
            response = client.get(feed_url)
            response.raise_for_status()
            root = ET.fromstring(response.text)
            source = _feed_source_title(root, feed_url)
            for node in _feed_nodes(root)[: limit * 2]:
                title = _child_text(node, ("title",))
                url = _child_text(node, ("link",))
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
                        published=_entry_published(node),
                        source=source,
                        section_zh=domain.section_zh,
                        section_en=domain.section_en,
                    )
                )
    items.sort(
        key=lambda x: x.published or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return items[:limit]
