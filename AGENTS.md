# Hermers — Cursor 作為大腦

本專案是 **AI 自動化剪報站** 的骨架。邏輯與產線之「推理、拆解、改稿」由 **Cursor 內的 Agent／Composer** 擔任；此倉庫只保存**可重現的程式、靜態產出與設定**，不把對話當成唯一真相來源。

## 目錄

| 路徑 | 說明 |
|------|------|
| `src/hermers/` | 可執行的編排與工具（抓取、組版、呼叫外部 API 等之後擴充） |
| `dist/` | 給 Cloudflare Pages 的靜態輸出（`index.html` 等） |
| `tools/` | 一次性腳本（例如 Git 推送） |
| `.cursor/rules/` | 給 Cursor 的專案規則，讓每次對話對齊同一套目標 |

## 與老闆協作方式

1. **需求與新聞網址**：在 Cursor 對話或 Composer 中說明；由 Agent 依本倉庫結構改 `src/`、更新 `dist/`。
2. **機密**：`GITHUB_TOKEN` 等只放在環境變數或本機 `.env`（已列入 `.gitignore`），永不寫入程式碼或 commit。
3. **部署**：靜態檔在 `dist/`；Cloudflare Pages 連結此 GitHub 倉庫後，以 `dist` 為輸出目錄（見 `wrangler.toml` 註解與官方文件）。

## 本機常用指令

**Windows（雙擊或 cmd）：**

| 檔案 | 說明 |
|------|------|
| `install.bat` | `pip install -e .` |
| `brain.bat` | 狀態檢查（`hermers.brain`） |
| `publish-dry.bat` | 預覽 git add / commit / push |
| `publish.bat` | 實際推送；可帶訊息：`publish.bat chore: update` |

雙擊執行時視窗會停在「按任意鍵」；若在已開啟的終端機不想暫停，可先設 `$env:HERMERS_NO_PAUSE=1`。

**PowerShell / 終端機：**

```powershell
python -m pip install -e .
python -m hermers.brain
python tools/git_publish.py --dry-run
```

首次建立遠端後再執行 `publish.bat` 或 `git_publish.py`（見腳本內說明）。
