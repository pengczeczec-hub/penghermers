# Cloudflare Python Worker（路線二）

Hermers 已改為以 **`uvx --from workers-py pywrangler deploy`** 部署 **Python Worker**（`WorkerEntrypoint`），不再使用 `wrangler pages deploy dist`。

## 你需要具備

- [uv](https://docs.astral.sh/uv/)（內建 **`uvx`**；建議：`winget install astral-sh.uv`）
- Node.js（pywrangler 依賴）
- Cloudflare 帳號並完成 `wrangler login`（或 CI 使用 `CLOUDFLARE_API_TOKEN`）

## 專案內關鍵檔案

| 檔案 | 用途 |
|------|------|
| `wrangler.toml` | Worker 名稱、`main.py`、`compatibility_flags = ["python_workers"]`、可選 `[triggers]` cron |
| `main.py` | Wrangler 入口；轉匯 `hermers.cf_worker.Default` |
| `src/hermers/cf_worker.py` | `WorkerEntrypoint`：`fetch`（HTTP）、`scheduled`（定時） |
| `src/hermers/worker_edge.py` | **僅含可在邊緣執行的輕量邏輯**；勿 import `pipeline` / `paths.repo_root` |
| `deploy_to_cloudflare.ps1` | 可選 git push → **`uvx --from workers-py pywrangler deploy`** |
| `pyproject.toml` | 專案依賴；可選 `[project.optional-dependencies] cloudflare` 供本機 `uv sync --extra cloudflare` 後使用 `uv run pywrangler dev`（非必須，開發可用上列 `uvx … dev`） |

## 部署指令

```powershell
cd "專案根目錄"
uvx --from workers-py pywrangler dev     # 本機開發
uvx --from workers-py pywrangler deploy  # 上線（CI／建置機建議用此，不需事先安裝 pywrangler）
```

若環境沒有 `uvx` 指令（較舊 uv），可改用：

```powershell
uv tool run --from workers-py pywrangler deploy
```

本機一鍵（含 push）：`.\deploy_to_cloudflare.ps1`  
（目前 git 分支若等於 `config/hermes.yaml` 的 **`github.branch`**（預設 `main`）→ 生產部署；否則加上 **`--env preview`**。可傳 **`-ProductionBranch develop`** 覆寫生產分支名稱。）

**為什麼用 `uvx`：** `uv run pywrangler` 依賴專案 venv 內已安裝的 `pywrangler`；許多 CI／建置映像沒有先 `uv sync --extra cloudflare`。`uvx --from workers-py` 會從 `workers-py` 取得並執行 `pywrangler`，符合 [Cloudflare Python Workers](https://developers.cloudflare.com/workers/languages/python/) 文件做法。

## 定時任務（scheduled）

1. 在 `wrangler.toml` 取消註解並設定 UTC cron，例如每日 02:00：

   ```toml
   [triggers]
   crons = ["0 2 * * *"]
   ```

2. `src/hermers/cf_worker.py` 內 `Default.scheduled` 會被 Cloudflare 呼叫；請把「每次排程要做的事」寫在 `worker_edge.scheduled_tick`（或拆成多個模組）。

3. 本機模擬可參考 [Cron Triggers](https://developers.cloudflare.com/workers/configuration/cron-triggers/) 與官方 Python 範例。

## HTTP 觸發（fetch）

| 路徑 | 說明 |
|------|------|
| `GET /` | 簡單 HTML 狀態頁 |
| `GET /api/health` | JSON 健康檢查 |
| `POST /api/trigger` | 手動觸發與排程相同的 `scheduled_tick`；若設定 `CRON_SECRET`，需標頭 `Authorization: Bearer <CRON_SECRET>` |

在 Cloudflare 儀表板為 Worker 設定 **變數／Secrets**（例如 `PIPELINE_WEBHOOK_URL`、`CRON_SECRET`），勿寫入 git。

## 如何把「剪報／自動化」搬進 Worker：架構建議

現有 `hermers.pipeline` 依賴 **本機目錄**（`staging/`、`data/`、`dist/`、`config/*.yaml`），在 Worker 上**沒有同一套檔案系統**，因此不適合整包直接 `import run_pipeline()` 上雲。

建議分層：

### A. 邊緣適合做的事（留在 `worker_edge` 或新模組）

- 驗簽 Webhook、聚合狀態、寫 **D1** / **KV** / **R2**
- 用 **httpx** 呼叫外部 HTTP（GitHub Actions、`repository_dispatch`、Telegram API、RSS 若體積與時間限制內可完成）
- 短任務佇列（**Queues**）或長流程（**Workflows**）

### B. 仍在本機或 GitHub Actions 做的事

- 現行 **`python -m hermers.pipeline`**（寫入 `staging/pending`、`dist/`）
- 需 **git / subprocess / 大量寫檔** 的流程

### C. 常見整合模式

1. **Worker 排程** → `POST` 到你的 **GitHub Actions workflow_dispatch**（或 `repository_dispatch`）→ Action 在 runner 上跑 `hermers-pipeline` 再 push。  
   - 將 webhook URL 設為 Secret：`PIPELINE_WEBHOOK_URL`（`worker_edge.scheduled_tick` 已預留範例）。
2. **Worker 只做 API**，剪報仍在 Telegram／本機觸發；Worker 提供健康檢查與手動 ` /api/trigger`。
3. **長期重構**：把「擷取文章、摘要」改成無狀態函式 + **R2** 存 HTML、**D1** 存 metadata，再逐步從 `pipeline` 抽離檔案依賴（工作量大，需分階段）。

## `wrangler.toml` 與 `pyproject.toml` 檢查清單

- [ ] `compatibility_flags` 含 **`python_workers`**
- [ ] `main` 指向 **`main.py`**
- [ ] `name` 與 Cloudflare 專案名稱一致（目前為 **`penghermers`**，可視需求修改）
- [ ] 已安裝 **uv**（含 uvx），且能執行 **`uvx --from workers-py pywrangler deploy`**
- [ ] 專案根目錄**沒有** `requirements.txt`（pywrangler 僅允許 `pyproject.toml`，若兩者並存會建置失敗）
- [ ] Python 版本：本機建議 **3.12+**（與 Cloudflare Python Workers 生態一致）

## 參考文件

- [Python Workers](https://developers.cloudflare.com/workers/languages/python/)
- [pywrangler / packages](https://developers.cloudflare.com/workers/languages/python/packages/)
- [Cron Triggers](https://developers.cloudflare.com/workers/configuration/cron-triggers/)
