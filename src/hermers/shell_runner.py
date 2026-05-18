from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import httpx

from hermers.env_load import load_dotenv
from hermers.subprocess_utf8 import run as sp_run
from hermers.hermes_config import HermesConfig, load_hermes_config
from hermers.paths import repo_root


def _verify_token_raw(token: str) -> dict:
    if not token:
        return {"ok": False, "error": "token 為空"}
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


def _verify_actions_github_token(token: str) -> dict:
    """GitHub Actions 的 GITHUB_TOKEN 多數無法通過 /user；改以目前倉庫驗證。"""
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if not repo or "/" not in repo:
        return {"ok": False, "error": "缺少 GITHUB_REPOSITORY（owner/repo）"}
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(
            f"https://api.github.com/repos/{repo}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
        )
    if resp.status_code == 200:
        return {"ok": True, "login": "github-actions", "name": "GITHUB_TOKEN"}
    return {"ok": False, "error": f"HTTP {resp.status_code}", "body": resp.text[:200]}


def _token_from_gh() -> str:
    """取得 gh 登入 token；略過環境變數內失效的 GITHUB_TOKEN。"""
    if not shutil.which("gh"):
        return ""
    env = os.environ.copy()
    env.pop("GITHUB_TOKEN", None)
    proc = sp_run(
        ["gh", "auth", "token"],
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def resolve_github_token() -> tuple[str, str]:
    """回傳 (token, 來源)。有效的 GITHUB_TOKEN 優先；否則用 gh（不受失效 .env 干擾）。"""
    load_dotenv()
    env_tok = os.environ.get("GITHUB_TOKEN", "").strip()
    if env_tok:
        check = _verify_token_raw(env_tok)
        if check.get("ok"):
            return env_tok, "GITHUB_TOKEN"
        # Actions 內建 token 無法通過 /user，改用 repo 讀取驗證
        if os.environ.get("GITHUB_ACTIONS") == "true":
            check_ci = _verify_actions_github_token(env_tok)
            if check_ci.get("ok"):
                return env_tok, "GITHUB_TOKEN"
        # 失效的 .env token 會干擾 gh；暫時移出環境
        os.environ.pop("GITHUB_TOKEN", None)

    gh_tok = _token_from_gh()
    if gh_tok:
        check = _verify_token_raw(gh_tok)
        if check.get("ok"):
            return gh_tok, "gh auth login"

    return "", "未設定（請 gh auth login，或更新 .env 的 GITHUB_TOKEN）"


def github_token() -> str:
    token, _ = resolve_github_token()
    return token


def verify_github_token() -> dict:
    token, source = resolve_github_token()
    if not token:
        return {
            "ok": False,
            "error": "未設定有效 token。請執行 gh auth login 或更新 .env 的 GITHUB_TOKEN",
        }
    info = _verify_token_raw(token)
    if info.get("ok"):
        info["source"] = source
        return info
    return {
        "ok": False,
        "error": f"{info.get('error')}（來源: {source}）",
        "hint": "建議：Remove-Item Env:GITHUB_TOKEN; gh auth login; 或 .env 填入 gh auth token 輸出",
    }


def ensure_git_remote(cfg: HermesConfig | None = None) -> str:
    cfg = cfg or load_hermes_config()
    root = repo_root()
    name = cfg.github_remote_name
    url = cfg.github_repo_url
    if not url:
        raise ValueError("config/hermes.yaml 未設定 github.repo_url")
    proc = sp_run(
        ["git", "remote", "get-url", name],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        sp_run(["git", "remote", "add", name, url], cwd=root, check=True)
    else:
        sp_run(["git", "remote", "set-url", name, url], cwd=root, check=True)
    return name


def git_push(
    *,
    dry_run: bool = False,
    message: str = "chore: publish via Hermes",
    cfg: HermesConfig | None = None,
) -> subprocess.CompletedProcess[str]:
    cfg = cfg or load_hermes_config()
    root = repo_root()
    token, source = resolve_github_token()

    remote = ensure_git_remote(cfg)
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"

    if dry_run:
        print("+", "git", "add", "-A")
        print("+", "git", "commit", "-m", message)
        print("+", "git", "push", remote, cfg.github_branch, f"  # auth: {source}")
        return subprocess.CompletedProcess([], 0, "", "")

    sp_run(["git", "add", "-A"], cwd=root, env=env, check=False)
    status = sp_run(
        ["git", "status", "--porcelain"],
        cwd=root,
        capture_output=True,
        text=True,
        env=env,
    )
    if status.stdout.strip():
        sp_run(
            ["git", "commit", "-m", message],
            cwd=root,
            env=env,
            check=False,
        )

    push_cmd = ["git", "push", remote, cfg.github_branch]

    # gh 已登入時，直接 push（使用 gh 的 git 憑證助手）
    if source == "gh auth login":
        proc = sp_run(push_cmd, cwd=root, env=env, capture_output=True, text=True)
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "").strip()
            if "not found" in err.lower():
                raise RuntimeError(
                    f"遠端倉庫不存在：{cfg.github_repo_url}\n"
                    "請到 GitHub 建立同名空倉庫，或修改 config/hermes.yaml 的 repo_url。"
                ) from None
            raise RuntimeError(err)
        return subprocess.CompletedProcess(push_cmd, 0, "pushed via gh", "")

    if not token:
        raise RuntimeError("無有效 GitHub 認證。請 gh auth login 或設定 GITHUB_TOKEN。")

    host_url = cfg.github_repo_url.replace("https://", f"https://x-access-token:{token}@")
    sp_run(
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
