from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def config_dir() -> Path:
    return repo_root() / "config"


def domains_config() -> Path:
    path = config_dir() / "domains.yaml"
    if path.is_file():
        return path
    return config_dir() / "domains.example.yaml"


def dist_dir() -> Path:
    return repo_root() / "dist"


def posts_dir() -> Path:
    return dist_dir() / "posts"


def staging_dir() -> Path:
    return repo_root() / "staging"


def pending_dir() -> Path:
    return staging_dir() / "pending"


def rejected_dir() -> Path:
    return staging_dir() / "rejected"


def data_dir() -> Path:
    return repo_root() / "data"


def seen_urls_path() -> Path:
    return data_dir() / "seen_urls.json"
