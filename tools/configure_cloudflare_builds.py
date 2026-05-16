#!/usr/bin/env python3
"""
以 Cloudflare Workers Builds API 設定建置（等同儀表板 Build 頁面）。

需在 .env 設定（勿 commit）：
  CLOUDFLARE_API_TOKEN   # 權限：Workers Builds Configuration (Edit)
  CLOUDFLARE_ACCOUNT_ID

用法：
  python tools/configure_cloudflare_builds.py
  python tools/configure_cloudflare_builds.py --trigger-build   # 設定後觸發生產建置
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from hermers.env_load import load_dotenv  # noqa: E402


def _api_token() -> str:
    load_dotenv()
    return (
        os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
        or os.environ.get("CF_API_TOKEN", "").strip()
    )


def _account_id() -> str:
    load_dotenv()
    return (
        os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
        or os.environ.get("CF_ACCOUNT_ID", "").strip()
    )


def _worker_name() -> str:
    toml = ROOT / "wrangler.toml"
    if not toml.is_file():
        return "penghermers"
    for line in toml.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("name") and "=" in line:
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return "penghermers"


def _client(token: str) -> httpx.Client:
    return httpx.Client(
        base_url="https://api.cloudflare.com/client/v4",
        headers={"Authorization": f"Bearer {token}"},
        timeout=60.0,
    )


def _worker_tag(client: httpx.Client, account_id: str, script_name: str) -> str:
    r = client.get(f"/accounts/{account_id}/workers/scripts")
    r.raise_for_status()
    data = r.json()
    if not data.get("success"):
        raise RuntimeError(data.get("errors") or "list workers failed")
    for item in data.get("result") or []:
        if item.get("id") == script_name:
            tag = item.get("tag")
            if tag:
                return str(tag)
    raise RuntimeError(f"找不到 Worker script：{script_name}")


def _list_triggers(client: httpx.Client, account_id: str, worker_tag: str) -> list[dict]:
    r = client.get(f"/accounts/{account_id}/builds/workers/{worker_tag}/triggers")
    r.raise_for_status()
    data = r.json()
    if not data.get("success"):
        raise RuntimeError(data.get("errors") or "list triggers failed")
    return list(data.get("result") or [])


def _patch_trigger(
    client: httpx.Client,
    account_id: str,
    trigger_uuid: str,
    *,
    deploy_command: str,
    build_command: str | None = "",
) -> None:
    body: dict = {"deploy_command": deploy_command}
    if build_command is not None:
        body["build_command"] = build_command
    r = client.patch(
        f"/accounts/{account_id}/builds/triggers/{trigger_uuid}",
        json=body,
    )
    r.raise_for_status()
    data = r.json()
    if not data.get("success"):
        raise RuntimeError(data.get("errors") or "patch trigger failed")


def _patch_env_vars(
    client: httpx.Client,
    account_id: str,
    trigger_uuid: str,
    variables: dict[str, str],
) -> None:
    r = client.patch(
        f"/accounts/{account_id}/builds/triggers/{trigger_uuid}/environment_variables",
        json={"variables": variables},
    )
    r.raise_for_status()
    data = r.json()
    if not data.get("success"):
        raise RuntimeError(data.get("errors") or "patch env vars failed")


def _trigger_build(client: httpx.Client, account_id: str, trigger_uuid: str) -> str:
    r = client.post(f"/accounts/{account_id}/builds/triggers/{trigger_uuid}/builds")
    r.raise_for_status()
    data = r.json()
    if not data.get("success"):
        raise RuntimeError(data.get("errors") or "create build failed")
    result = data.get("result") or {}
    return str(result.get("build_uuid") or result.get("id") or "")


def _is_production_trigger(t: dict) -> bool:
    includes = t.get("branch_includes") or []
    name = (t.get("trigger_name") or "").lower()
    if "main" in includes and "*" not in includes:
        return True
    if "production" in name and "non-production" not in name and "preview" not in name:
        return True
    if includes == ["main"]:
        return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="設定 Cloudflare Workers Builds（API）")
    parser.add_argument(
        "--trigger-build",
        action="store_true",
        help="設定完成後對生產 trigger 觸發一次新建置",
    )
    args = parser.parse_args()

    token = _api_token()
    account_id = _account_id()
    if not token or not account_id:
        print(
            "請在 .env 設定 CLOUDFLARE_API_TOKEN 與 CLOUDFLARE_ACCOUNT_ID。\n"
            "Token 需含「Workers Builds Configuration」Edit 權限。\n"
            "帳號 ID：Cloudflare 儀表板右側或 Workers 概覽 URL 中的 account id。\n"
            "或改用手動：docs/CLOUDFLARE_WORKER.md「疑難」一節。",
            file=sys.stderr,
        )
        return 1

    script_name = _worker_name()
    prod_cmd = "bash cloudflare-build.sh"
    preview_cmd = "bash cloudflare-build.sh --env preview"
    build_env = {"SKIP_DEPENDENCY_INSTALL": "1"}

    with _client(token) as client:
        tag = _worker_tag(client, account_id, script_name)
        print(f"Worker: {script_name}  tag={tag}")

        triggers = _list_triggers(client, account_id, tag)
        if not triggers:
            print("此 Worker 沒有 Builds trigger，請先在儀表板連接 Git 倉庫。", file=sys.stderr)
            return 1

        prod_uuid = None
        for t in triggers:
            uid = str(t.get("trigger_uuid") or "")
            if not uid:
                continue
            is_prod = _is_production_trigger(t)
            cmd = prod_cmd if is_prod else preview_cmd
            label = "生產" if is_prod else "預覽/非生產"
            print(f"\n[{label}] {t.get('trigger_name')}  {uid}")
            print(f"  deploy_command <- {cmd}")
            _patch_trigger(
                client,
                account_id,
                uid,
                deploy_command=cmd,
                build_command="",
            )
            _patch_env_vars(client, account_id, uid, build_env)
            print("  SKIP_DEPENDENCY_INSTALL=1")
            if is_prod:
                prod_uuid = uid

        if args.trigger_build and prod_uuid:
            build_id = _trigger_build(client, account_id, prod_uuid)
            print(f"\n已觸發生產建置 build_uuid={build_id}")

    print("\n完成。請到 Cloudflare Deployments 查看日誌（建議 Clear build cache 後確認 commit 為最新）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
