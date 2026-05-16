# Hermers — 專屬員工（Cursor API 大腦）

## 大腦 = Cursor，不是 GPT

- 自然語言推理透過 **`CURSOR_API_KEY`** + 官方 **`@cursor/sdk`**
- 在本機對 **Hermers 專案目錄** 執行 Agent（`composer-2` 等 Cursor 模型）
- **消耗 Cursor 帳號額度**，不使用 OpenAI API Key

## 安裝 Cursor 大腦

```powershell
# 1. Cursor 儀表板 → Integrations → 建立 User API Key
# 2. 寫入 .env：
#    CURSOR_API_KEY=cursor_...
#    HERMES_LLM_PROVIDER=cursor

install-cursor-brain.bat   # 安裝 Node 依賴 @cursor/sdk
python -m pip install -e .
telegram-bot.bat             # 常駐
```

## 運作方式

```
Telegram 自然語言
  → Hermes Agent（Cursor SDK 選工具）
  → 本機執行 pipeline / deploy / 擷取網址…
  → 結果回 Telegram
```

無 Cursor Key 時退回**關鍵字規則**（部署、剪報、貼網址仍可用）。

## 擴充技能

在 `src/hermers/agent/tools.py` 註冊新工具。

## CLI

```powershell
python hermes_main.py agent 幫我部署網站並說明做了什麼
```
