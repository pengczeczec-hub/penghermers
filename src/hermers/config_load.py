from __future__ import annotations

from dataclasses import dataclass, field

import yaml

from hermers.paths import domains_config


@dataclass
class DomainConfig:
    id: str
    name: str
    keywords: list[str] = field(default_factory=list)
    rss: list[str] = field(default_factory=list)
    section_zh: str | None = None
    section_en: str | None = None


@dataclass
class AppConfig:
    max_items: int = 5
    # 各網域 RSS 先取滿此上限（過濾後）再全域排序挑選 max_items；越大越容易涵蓋全市場再精選
    fetch_pool: int = 40
    domains: list[DomainConfig] = field(default_factory=list)


def load_config() -> AppConfig:
    path = domains_config()
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    domains = []
    for item in raw.get("domains") or []:
        sz = item.get("section_zh")
        se = item.get("section_en")
        domains.append(
            DomainConfig(
                id=str(item["id"]),
                name=str(item.get("name") or item["id"]),
                keywords=[str(k) for k in (item.get("keywords") or [])],
                rss=[str(u) for u in (item.get("rss") or [])],
                section_zh=str(sz).strip() if sz else None,
                section_en=str(se).strip() if se else None,
            )
        )
    max_items = int(raw.get("max_items") or 5)
    fetch_pool = int(raw.get("fetch_pool") or max(max_items * 5, 40))
    return AppConfig(
        max_items=max_items,
        fetch_pool=fetch_pool,
        domains=domains,
    )
