from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from hermers.paths import pending_dir, posts_dir, rejected_dir
from hermers.site import rebuild_index, write_review_page
from hermers.telegram_notify import notify_review_action


def _pending_folder(draft_id: str) -> Path:
    folder = pending_dir() / draft_id
    if not folder.is_dir():
        raise SystemExit(f"找不到待審草稿：{draft_id}")
    return folder


def list_pending() -> int:
    rows = sorted(pending_dir().glob("*/meta.json")) if pending_dir().is_dir() else []
    if not rows:
        print("（無待審草稿）")
        return 0
    for meta_path in rows:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        print(f"{meta['id']}\t{meta.get('domain_name', '')}\t{meta.get('title', '')}")
    review = write_review_page()
    print(f"\n審核頁：{review}")
    return 0


def approve(draft_id: str) -> int:
    folder = _pending_folder(draft_id)
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    draft_html = folder / "draft.html"
    if not draft_html.is_file():
        raise SystemExit(f"缺少 draft.html：{draft_id}")

    posts_dir().mkdir(parents=True, exist_ok=True)
    out_html = posts_dir() / f"{draft_id}.html"
    out_meta = posts_dir() / f"{draft_id}.json"
    shutil.copy2(draft_html, out_html)
    meta["status"] = "approved"
    meta["approved_at"] = datetime.now(timezone.utc).isoformat()
    out_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.rmtree(folder)
    rebuild_index()
    write_review_page()
    notify_review_action(action="通過審核", draft_id=draft_id, title=meta.get("title", ""))
    print(f"已通過審核 → dist/posts/{draft_id}.html")
    print("若要上線 GitHub，請執行 publish.bat（不會自動推送）。")
    return 0


def reject(draft_id: str) -> int:
    folder = _pending_folder(draft_id)
    rejected_dir().mkdir(parents=True, exist_ok=True)
    dest = rejected_dir() / draft_id
    if dest.exists():
        shutil.rmtree(dest)
    shutil.move(str(folder), str(dest))
    write_review_page()
    meta = json.loads((dest / "meta.json").read_text(encoding="utf-8"))
    notify_review_action(action="拒絕", draft_id=draft_id, title=meta.get("title", ""))
    print(f"已拒絕並移至 staging/rejected/{draft_id}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Hermers 待審：列出 / 通過 / 拒絕")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="列出待審草稿")

    p_ok = sub.add_parser("approve", help="通過審核並寫入 dist/posts/")
    p_ok.add_argument("id", help="草稿 ID")

    p_no = sub.add_parser("reject", help="拒絕草稿")
    p_no.add_argument("id", help="草稿 ID")

    args = parser.parse_args()
    if args.cmd == "list":
        raise SystemExit(list_pending())
    if args.cmd == "approve":
        raise SystemExit(approve(args.id))
    if args.cmd == "reject":
        raise SystemExit(reject(args.id))


if __name__ == "__main__":
    main()
