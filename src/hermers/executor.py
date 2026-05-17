"""
Hermes 主動執行器：Telegram 指令直接驅動本機 Python / Git / 部署腳本。
不產生需手動開啟的 CURSOR_SPEC；僅在失敗時回報請使用者介入。
"""

from __future__ import annotations

import html
import io
import os
import re
import sys
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from datetime import datetime, timezone

from hermers.discover import FeedItem
from hermers.subprocess_utf8 import run as sp_run
from hermers.draft import write_pending
from hermers.fetch import fetch_article
from hermers.env_load import load_dotenv
from hermers.hermes_config import HermesConfig, load_hermes_config
from hermers.paths import pending_dir, repo_root
from hermers.pipeline import run_pipeline
from hermers.review import approve, list_pending
from hermers.shell_runner import git_push, verify_github_token
from hermers.site import rebuild_index
from hermers.site_live import check_site_live, public_site_url, site_live_html_block


@dataclass
class RunResult:
    ok: bool
    message: str


def _slug(text: str, max_len: int = 40) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "-", text, flags=re.UNICODE).strip("-").lower()
    return (s[:max_len] or "post").strip("-")


def _capture(fn) -> tuple[bool, str]:
    buf = io.StringIO()
    try:
        with redirect_stdout(buf), redirect_stderr(buf):
            code = fn()
        out = buf.getvalue().strip()
        if code is not None and code != 0:
            return False, out or f"結束碼 {code}"
        return True, out
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


class HermesExecutor:
    def __init__(self, cfg: HermesConfig | None = None) -> None:
        self.cfg = cfg or load_hermes_config()

    def status(self) -> RunResult:
        gh = verify_github_token()
        pending = (
            len(list(pending_dir().glob("*/meta.json"))) if pending_dir().is_dir() else 0
        )
        if gh.get("ok"):
            gh_line = f"GitHub: {html.escape(str(gh.get('login')))} ({html.escape(str(gh.get('source', '')))})"
        else:
            gh_line = html.escape(str(gh.get("error", "未設定")))
        site_url = public_site_url()
        live = check_site_live(site_url)
        text = (
            "<b>Hermes 執行器</b>\n"
            f"{gh_line}\n"
            f"{site_live_html_block(live)}\n"
            f"待審 staging: {pending} 則\n"
            f"目標: <code>{html.escape(self.cfg.github_repo_url)}</code>"
        )
        return RunResult(True, text)

    def ingest_url(self, url: str, *, push: bool = False) -> RunResult:
        from hermers.url_policy import is_own_site_url

        url = url.strip().rstrip(".,)")
        if is_own_site_url(url):
            live = check_site_live(url)
            msg = "<b>這是 Hermers 自己的網站</b>，不會再做成剪報。\n" + site_live_html_block(live)
            if live.online:
                msg += "\n若要同步本機 dist 變更到雲端，請傳 <code>/deploy</code>。"
            else:
                msg += "\n若剛部署完仍顯示離線，請稍候再試或傳 <code>/status</code>。"
            return RunResult(True, msg)
        try:
            extract = fetch_article(url)
        except Exception as exc:  # noqa: BLE001
            return RunResult(
                False,
                f"<b>擷取失敗</b>，需請您介入：\n<code>{html.escape(str(exc))}</code>",
            )

        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        draft_id = f"{stamp}-{_slug(extract.title or url)}"
        item = FeedItem(
            domain_id="manual",
            domain_name="Telegram",
            title=extract.title or url,
            url=url,
            published=datetime.now(timezone.utc),
            source="telegram",
        )
        folder = pending_dir() / draft_id
        write_pending(folder, item=item, extract=extract, draft_id=draft_id)
        try:
            approve(draft_id, notify=False)
        except SystemExit as exc:
            return RunResult(
                False,
                f"<b>發布失敗</b>：{html.escape(str(exc.args[0] if exc.args else exc))}",
            )
        rebuild_index()

        lines = [
            "<b>剪報完成</b>",
            f"<code>{html.escape(draft_id)}</code>",
            html.escape(extract.title or url)[:120],
        ]
        if push:
            pub = self.publish("chore: digest from telegram url")
            lines.append(pub.message)
            return RunResult(pub.ok, "\n".join(lines))
        live = check_site_live()
        lines.append("已寫入本機 dist。")
        lines.append(site_live_html_block(live))
        if not live.online:
            lines.append("雲端尚未就緒時請傳 <code>/deploy</code>。")
        elif push:
            pass
        else:
            lines.append("本機與雲端內容可能不同步；要推送請傳 <code>/deploy</code>。")
        return RunResult(True, "\n".join(lines))

    def run_pipeline(self, *, push: bool = False) -> RunResult:
        pending_dir().mkdir(parents=True, exist_ok=True)
        before = {p.name for p in pending_dir().iterdir() if p.is_dir()}

        ok, log = _capture(lambda: run_pipeline(dry_run=False))
        if not ok:
            return RunResult(
                False,
                f"<b>管線失敗</b>，需介入：\n<pre>{html.escape(log[-1500:])}</pre>",
            )

        after = {p.name for p in pending_dir().iterdir() if p.is_dir()}
        approved: list[str] = []
        for draft_id in sorted(after - before):
            try:
                approve(draft_id)
                approved.append(draft_id)
            except (SystemExit, Exception):  # noqa: BLE001
                continue

        msg = f"<b>管線完成</b>\n已發布 {len(approved)} 則至 dist/posts/"
        if approved:
            msg += "\n" + "\n".join(f"• <code>{html.escape(i)}</code>" for i in approved[:8])
        if push:
            pub = self.publish("chore: pipeline auto publish")
            msg += "\n\n" + pub.message
            return RunResult(pub.ok, msg)
        msg += "\n\n傳 /deploy 可推送 GitHub。"
        return RunResult(True, msg)

    def publish(self, message: str = "chore: publish via Hermes") -> RunResult:
        try:
            git_push(dry_run=False, message=message, cfg=self.cfg)
        except Exception as exc:  # noqa: BLE001
            return RunResult(
                False,
                f"<b>推送失敗</b>，需介入：\n<code>{html.escape(str(exc))}</code>",
            )
        return RunResult(
            True,
            f"<b>已推送到 GitHub</b>\n<code>{html.escape(self.cfg.github_repo_url)}</code>",
        )

    def deploy(self) -> RunResult:
        pub = self.publish("chore: deploy via Hermes")
        if not pub.ok:
            return pub

        script = repo_root() / "deploy_to_cloudflare.ps1"
        if not script.is_file():
            return RunResult(True, pub.message + "\n\n（無 deploy 腳本，僅完成 git push）")

        proc = sp_run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
                "-SkipPush",
            ],
            cwd=repo_root(),
            capture_output=True,
            text=True,
        )
        tail = (proc.stdout or proc.stderr or "").strip()[-800:]
        if proc.returncode != 0:
            return RunResult(
                False,
                pub.message
                + f"\n\n<b>Cloudflare 腳本失敗</b>：\n<pre>{html.escape(tail)}</pre>",
            )
        return RunResult(
            True,
            "<b>部署完成</b>\n"
            + pub.message
            + "\n\nCloudflare：Python Worker（pywrangler）。請在儀表板確認 Workers 版本與路由。",
        )
