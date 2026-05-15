from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from hermers.paths import repo_root


@dataclass
class HermesConfig:
    github_repo_url: str
    github_branch: str
    github_remote_name: str
    cloudflare_output_dir: str
    tasks_pending: Path
    tasks_done: Path


def load_hermes_config() -> HermesConfig:
    path = repo_root() / "config" / "hermes.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else {}
    gh = raw.get("github") or {}
    cf = raw.get("cloudflare") or {}
    cu = raw.get("cursor") or {}
    root = repo_root()
    return HermesConfig(
        github_repo_url=str(gh.get("repo_url", "")),
        github_branch=str(gh.get("branch", "main")),
        github_remote_name=str(gh.get("remote_name", "deploy")),
        cloudflare_output_dir=str(cf.get("output_dir", "dist")),
        tasks_pending=root / str(cu.get("tasks_pending", "tasks/pending")),
        tasks_done=root / str(cu.get("tasks_done", "tasks/done")),
    )
