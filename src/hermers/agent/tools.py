from __future__ import annotations

import json
import re
from typing import Any, Callable

from hermers.executor import HermesExecutor, RunResult

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


_register("deploy_site", "推送 GitHub 並執行 Cloudflare 部署流程", _tool_deploy)
_register("publish_git", "將目前專案推送到 GitHub", _tool_publish)
_register("run_digest_pipeline", "從 RSS 抓取熱門新聞、生成剪報並寫入 dist", _tool_pipeline)
_register("ingest_news_url", "擷取單一新聞網址並生成剪報頁（args: url, push?）", _tool_ingest_url)
_register("system_status", "查看 Hermes / GitHub / 待審狀態", _tool_status)
_register("list_capabilities", "列出所有可用工具", _tool_help)


def extract_urls(text: str) -> list[str]:
    return re.findall(r"https?://\S+", text)
