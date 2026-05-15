# Hermers / Hermes — Cursor 為唯一 AI 引擎

## 核心邏輯

- **Hermes（本倉庫程式）**：任務編排 — 收 Telegram、產生任務清單、呼叫本機終端機（git、部署腳本）。
- **Cursor（您開啟的 IDE Agent）**：唯一推理引擎 — 讀 `tasks/pending/*/CURSOR_SPEC.md` 並在工作區執行。
- **不**在 Hermes 內呼叫 OpenAI / Claude 等外部 LLM API。

## 目錄

| 路徑 | 說明 |
|------|------|
| `hermes_interface.py` | 編排 CLI：建立 / 列出 / 完成任務 |
| `tasks/pending/` | 待 Cursor 執行的任務（含 CURSOR_SPEC.md） |
| `tasks/done/` | 已完成任務 |
| `config/hermes.yaml` | GitHub 目標倉庫、Cloudflare 輸出目錄 |
| `src/hermers/` | 管線、Telegram、任務產生器 |
| `dist/` | 靜態站輸出 |
| `deploy_to_cloudflare.ps1` | 部署輔助（由 Cursor 在終端機執行） |

## 工作流程

1. **指令接收**：Telegram → `telegram-bot.bat` → 建立 `tasks/pending/<id>/`
2. **大腦推演**：您在 **Cursor** 開啟任務內 `CURSOR_SPEC.md`，由 Agent 執行
3. **系統執行**：Agent 在終端機跑 git / pipeline / `deploy_to_cloudflare.ps1`（讀 `$env:GITHUB_TOKEN`）
4. **審核**：剪報仍走 `staging/` 待審，通過後才發布
5. **完成**：`python hermes_interface.py complete <task_id>`

## 本機 .bat（精簡後）

| 檔案 | 用途 |
|------|------|
| `install.bat` | 安裝 Python 套件 |
| `hermes.bat` | 編排 CLI（status / task / test-github） |
| `telegram-bot.bat` | Telegram → 建立 Cursor 任務（需常駐） |

## 常用指令

```powershell
python -m pip install -e .
python hermes_interface.py status
python hermes_interface.py task new -k digest_pipeline -t "今日剪報"
python hermes_interface.py task list
python tools/test_github_push.py          # 驗證 GITHUB_TOKEN
python tools/test_github_push.py --push   # 推送到 config/hermes.yaml 倉庫
```

## 密鑰

- `GITHUB_TOKEN`、`TELEGRAM_*` 僅來自環境變數或 `.env`（不 commit）。
- 預設推送目標：`config/hermes.yaml` → `auto-news-site`（可改）。
