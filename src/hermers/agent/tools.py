from __future__ import annotations

import html
import json
import os
import re
from typing import Any, Callable

from hermers.env_load import load_dotenv
from hermers.executor import HermesExecutor, RunResult
from hermers.hermes_config import load_hermes_config

ToolFn = Callable[[dict[str, Any]], RunResult]

_REGISTRY: dict[str, tuple[str, ToolFn]] = {}


def _register(name: str, description: str, fn: ToolFn) -> None:
    _REGISTRY[name] = (description, fn)


def list_tools() -> dict[str, str]:
    return {name: desc for name, (desc, _) in _REGISTRY.items()}


def run_tool(name: str, args: dict[str, Any]) -> RunResult:
    if name not in _REGISTRY:
        return RunResult(False, f"未知工具：{name}")
    _, fn = _REGISTRY[name]
    return fn(args or {})


def tools_schema_text() -> str:
    lines = []
    for name, (desc, _) in _REGISTRY.items():
        lines.append(f"- {name}: {desc}")
    return "\n".join(lines)


def _ex() -> HermesExecutor:
    return HermesExecutor()


def _tool_deploy(_: dict) -> RunResult:
    return _ex().deploy()


def _tool_publish(_: dict) -> RunResult:
    return _ex().publish()


def _tool_pipeline(_: dict) -> RunResult:
    push = bool(_.get("push"))
    return _ex().run_pipeline(push=push)


def _tool_ingest_url(args: dict) -> RunResult:
    url = str(args.get("url", "")).strip()
    if not url:
        return RunResult(False, "缺少 url")
    push = bool(args.get("push"))
    return _ex().ingest_url(url, push=push)


def _tool_status(_: dict) -> RunResult:
    return _ex().status()


def _tool_help(_: dict) -> RunResult:
    return RunResult(
        True,
        "<b>Hermes 工具</b>\n<pre>"
        + "\n".join(f"{k}: {v}" for k, v in list_tools().items())
        + "</pre>",
    )


def _tool_site_url(_: dict) -> RunResult:
    load_dotenv()
    site = os.environ.get("SITE_PUBLIC_URL", "").strip()
    cfg = load_hermes_config()
    lines = ["<b>網站／網址</b>"]
    if site:
        lines.append(f"對外網址（.env）：\n<code>{html.escape(site)}</code>")
    else:
        lines.append(
            "尚未設定 <code>SITE_PUBLIC_URL</code>。\n"
            "Cloudflare Worker 部署成功後，請在 .env 填入 Workers 網址，例如：\n"
            "<code>https://penghermers.你的子網域.workers.dev</code>"
        )
    lines.append(f"\nGitHub：\n<code>{html.escape(cfg.github_repo_url)}</code>")
    lines.append("\n查狀態請傳 <code>/status</code> 或「狀態」。")
    return RunResult(True, "\n".join(lines))


_register("deploy_site", "推送 GitHub 並執行 Cloudflare 部署流程", _tool_deploy)
_register("publish_git", "將目前專案推送到 GitHub", _tool_publish)
_register("run_digest_pipeline", "從 RSS 抓取熱門新聞、生成剪報並寫入 dist", _tool_pipeline)
_register("ingest_news_url", "擷取單一新聞網址並生成剪報頁（args: url, push?）", _tool_ingest_url)
_register("system_status", "查看 Hermes / GitHub / 待審狀態", _tool_status)
_register("site_url_info", "回報對外網站網址與 GitHub 目標", _tool_site_url)
_register("list_capabilities", "列出所有可用工具", _tool_help)


def extract_urls(text: str) -> list[str]:
    return re.findall(r"https?://\S+", text)
