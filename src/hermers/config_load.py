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


@dataclass
class AppConfig:
    max_items: int = 5
    domains: list[DomainConfig] = field(default_factory=list)


def load_config() -> AppConfig:
    path = domains_config()
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    domains = []
    for item in raw.get("domains") or []:
        domains.append(
            DomainConfig(
                id=str(item["id"]),
                name=str(item.get("name") or item["id"]),
                keywords=[str(k) for k in (item.get("keywords") or [])],
                rss=[str(u) for u in (item.get("rss") or [])],
            )
        )
    return AppConfig(max_items=int(raw.get("max_items") or 5), domains=domains)
