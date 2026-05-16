from __future__ import annotations

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermers.hermes_config import HermesConfig, load_hermes_config

PROMPTS: dict[str, str] = {
    "digest_pipeline": """# Cursor 任務：執行剪報管線

請在本工作區**直接於終端機**完成（不要用外部 AI API）：

1. `python -m pip install -e .`（若尚未安裝）
2. `python -m hermers.pipeline`
3. 開啟 `staging/review.html`，檢查 `staging/pending/` 草稿
4. 回報待審 ID 與標題列表

**不要**自動 `git push`；發布需等使用者審核後另建 `git_publish` 任務。
""",
    "git_publish": """# Cursor 任務：推送到 GitHub

1. 確認 `dist/` 與待審內容已就緒且使用者已審核
2. 讀取環境變數 `GITHUB_TOKEN`（勿寫入檔案）
3. 在終端機執行：
   - `python tools/test_github_push.py`（先驗證 token）
   - `python tools/git_publish.py -m "chore: publish via Hermes/Cursor"`
4. 回報 push 結果

若 token 未設定，請提示使用者在 PowerShell 設定 `$env:GITHUB_TOKEN` 或 `gh auth login`。
""",
    "deploy_cloudflare": """# Cursor 任務：部署到 Cloudflare（Python Worker）

1. 安裝 `uv` 與 Node.js；專案根：`uv sync --extra cloudflare`
2. 在終端機執行：`powershell -ExecutionPolicy Bypass -File .\\deploy_to_cloudflare.ps1`
3. 部署使用 `uv run pywrangler deploy`；行為見 `docs/CLOUDFLARE_WORKER.md` 與 `src/hermers/cf_worker.py`
4. 回報 Workers 儀表板版本與路由結果
""",
    "user_request": """# Cursor 任務：使用者自訂需求

請閱讀下方「使用者原文」，在本工作區完成對應修改或終端機指令。
遵守 `AGENTS.md`：密鑰僅能來自環境變數，勿寫入 commit。
""",
}


def _slug(text: str, n: int = 32) -> str:
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "-", text, flags=re.UNICODE).strip("-").lower()
    return (s[:n] or "task").strip("-")


def create_task(
    kind: str,
    *,
    title: str,
    payload: dict[str, Any] | None = None,
    source: str = "manual",
    user_text: str = "",
    cfg: HermesConfig | None = None,
) -> Path:
    cfg = cfg or load_hermes_config()
    cfg.tasks_pending.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    task_id = f"{stamp}-{_slug(title)}"
    folder = cfg.tasks_pending / task_id
    folder.mkdir(parents=True, exist_ok=False)

    meta = {
        "id": task_id,
        "kind": kind,
        "title": title,
        "source": source,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload or {},
    }
    (folder / "task.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    base_prompt = PROMPTS.get(kind, PROMPTS["user_request"])
    spec = f"""{base_prompt}

---

## 任務中繼資料

- **task_id**: `{task_id}`
- **kind**: `{kind}`
- **source**: {source}

## 使用者原文 / 補充

{user_text or "（無）"}

## 完成後

1. 在終端機確認結果
2. 將本資料夾移至 `tasks/done/{task_id}`（或執行 `python hermes_interface.py complete {task_id}`）
"""
    (folder / "CURSOR_SPEC.md").write_text(spec, encoding="utf-8")

    checklist = [
        f"- [ ] 閱讀 CURSOR_SPEC.md（task: {task_id}）",
        "- [ ] 在 Cursor 終端機執行必要指令",
        "- [ ] 確認 dist/ 或 git 狀態",
        "- [ ] 標記任務完成",
    ]
    (folder / "CHECKLIST.md").write_text("\n".join(checklist) + "\n", encoding="utf-8")
    return folder


def list_tasks(cfg: HermesConfig | None = None, *, pending_only: bool = True) -> list[dict]:
    cfg = cfg or load_hermes_config()
    base = cfg.tasks_pending if pending_only else cfg.tasks_done
    if not base.is_dir():
        return []
    out: list[dict] = []
    for p in sorted(base.glob("*/task.json")):
        out.append(json.loads(p.read_text(encoding="utf-8")))
    return out


def complete_task(task_id: str, cfg: HermesConfig | None = None) -> Path:
    cfg = cfg or load_hermes_config()
    src = cfg.tasks_pending / task_id
    if not src.is_dir():
        raise FileNotFoundError(f"找不到待辦任務：{task_id}")
    dest = cfg.tasks_done / task_id
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.move(str(src), str(dest))
    meta_path = dest / "task.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["status"] = "done"
    meta["completed_at"] = datetime.now(timezone.utc).isoformat()
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return dest
