# Antigravity Gemini-Telegram Bridge 🚀

這是一個整合了 **Google Gemini 雲端 API** 與 **Ollama 本地模型 (Gemma 3n:e2b)** 的 Telegram 機器人，並透過 **Model Context Protocol (MCP)** 支援 Google Workspace (Gmail, Drive) 工具調用。

## 🌟 功能特點
- **雙模式啟動**：支援「連線 (Online)」與「離線 (Offline)」模式切換。
- **本地工具能力**：離線模式下依然可以使用 Google Workspace 工具。
- **自動模型維護**：自動清理大體積模型，確保在 16GB RAM 的 Mac 上順暢執行。
- **安全管理**：所有 API Key 均透過環境變數隔離，避免洩漏。

## 🛠️ 安裝步驟

### 1. 複製專案
```bash
git clone <your-repo-url>
cd gemini-bot
```

### 2. 安裝 Python 依賴
```bash
pip install -r requirements.txt
```
*(如果沒有 requirements.txt，請執行 `pip install python-telegram-bot ollama mcp google-generativeai python-dotenv`)*

### 3. 設定環境變數
將 `.env.example` 重新命名為 `.env` 並填入您的金鑰：
```bash
cp .env.example .env
# 使用編輯器開啟 .env 並填入資訊
```

## 🚀 啟動機器人
```bash
python tg_bridge.py
```
啟動後，依據提示輸入 `1` 或 `2` 即可進入對應模式。

## 🔒 安全提醒
請勿將 `.env` 檔案上傳到任何公開平台。專案已內建 `.gitignore` 確保安全。
