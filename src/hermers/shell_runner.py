from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import httpx

from hermers.env_load import load_dotenv
from hermers.hermes_config import HermesConfig, load_hermes_config
from hermers.paths import repo_root


def github_token() -> str:
    load_dotenv()
    return os.environ.get("GITHUB_TOKEN", "").strip()


def verify_github_token() -> dict:
    token = github_token()
    if not token:
        return {"ok": False, "error": "GITHUB_TOKEN 未設定"}
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
        )
    if resp.status_code != 200:
        return {"ok": False, "error": f"HTTP {resp.status_code}", "body": resp.text[:200]}
    data = resp.json()
    return {"ok": True, "login": data.get("login"), "name": data.get("name")}


def ensure_git_remote(cfg: HermesConfig | None = None) -> str:
    cfg = cfg or load_hermes_config()
    root = repo_root()
    name = cfg.github_remote_name
    url = cfg.github_repo_url
    if not url:
        raise ValueError("config/hermes.yaml 未設定 github.repo_url")
    proc = subprocess.run(
        ["git", "remote", "get-url", name],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        subprocess.run(["git", "remote", "add", name, url], cwd=root, check=True)
    else:
        subprocess.run(["git", "remote", "set-url", name, url], cwd=root, check=True)
    return name


def git_push(
    *,
    dry_run: bool = False,
    message: str = "chore: publish via Hermes",
    cfg: HermesConfig | None = None,
) -> subprocess.CompletedProcess[str]:
    cfg = cfg or load_hermes_config()
    root = repo_root()
    token = github_token()
    if not token:
        raise RuntimeError("GITHUB_TOKEN 未設定")

    remote = ensure_git_remote(cfg)
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"

    if dry_run:
        print("+", "git", "add", "-A")
        print("+", "git", "commit", "-m", message)
    else:
        subprocess.run(["git", "add", "-A"], cwd=root, env=env, check=False)
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            capture_output=True,
            text=True,
            env=env,
        )
        if status.stdout.strip():
            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=root,
                env=env,
                check=False,
            )

    push_cmd = ["git", "push", remote, cfg.github_branch]
    if dry_run:
        print("+", " ".join(push_cmd))
        return subprocess.CompletedProcess(push_cmd, 0, "", "")

    # 使用 Bearer token 作為 HTTPS 認證（不寫入 remote URL 永久儲存）
    host_url = cfg.github_repo_url.replace("https://", f"https://x-access-token:{token}@")
    subprocess.run(
        ["git", "push", host_url, f"HEAD:{cfg.github_branch}"],
        cwd=root,
        env=env,
        check=True,
    )
    return subprocess.CompletedProcess(push_cmd, 0, "pushed", "")


def run_powershell(script: Path, *args: str) -> int:
    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        *args,
    ]
    return subprocess.run(cmd, cwd=repo_root()).returncode
