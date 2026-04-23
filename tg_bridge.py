import logging
import os
import json
import asyncio
import subprocess
from typing import List, Dict, Any

import ollama
import google.generativeai as genai
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
WHITE_LIST_ID = int(os.getenv("WHITE_LIST_ID", "0"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Credentials for Google Workspace MCP
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- MCP Tool Mapper ---
def mcp_tool_to_ollama(tool: Any) -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.inputSchema
        }
    }

# --- Orchestration Logic ---
class HybridBridge:
    def __init__(self, mode: str, local_model: str = "gemma3n:e2b"):
        self.mode = mode
        self.local_model = local_model
        
        # MCP Setup
        mcp_env = os.environ.copy()
        mcp_env["GOOGLE_CLIENT_ID"] = GOOGLE_CLIENT_ID
        mcp_env["GOOGLE_CLIENT_SECRET"] = GOOGLE_CLIENT_SECRET
        self.server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@presto-ai/google-workspace-mcp"],
            env=mcp_env
        )
        self.tools = []
        self._session = None
        self._client_cm = None
        self._lock = asyncio.Lock()

        # Gemini Setup
        if mode == 'online':
            genai.configure(api_key=GEMINI_API_KEY)
            self.gemini_model = genai.GenerativeModel('gemini-2.0-flash-lite')

    async def start(self):
        logger.info(f"Initializing {self.mode} bridge...")
        try:
            self._client_cm = stdio_client(self.server_params)
            read, write = await self._client_cm.__aenter__()
            self._session = ClientSession(read, write)
            await self._session.__aenter__()
            await self._session.initialize()
            
            mcp_tools = await self._session.list_tools()
            self.tools = [mcp_tool_to_ollama(t) for t in mcp_tools.tools]
            logger.info(f"Connected to MCP. Found {len(self.tools)} tools.")
        except Exception as e:
            logger.error(f"MCP Start Error: {e}")
            raise

    async def chat(self, user_input: str) -> str:
        if not self._session:
            await self.start()

        if self.mode == 'offline':
            return await self._chat_ollama(user_input)
        else:
            return await self._chat_gemini(user_input)

    async def _chat_ollama(self, user_input: str) -> str:
        messages = [
            {"role": "system", "content": "You are Antigravity, a local AI assistant. Use Google Workspace tools to help. Be terse."},
            {"role": "user", "content": user_input}
        ]
        async with self._lock:
            while True:
                response = await asyncio.to_thread(ollama.chat, model=self.local_model, messages=messages, tools=self.tools)
                msg = response.get("message", {})
                messages.append(msg)
                if not msg.get("tool_calls"): return msg.get("content", "")
                for tc in msg["tool_calls"]:
                    res = await self._session.call_tool(tc["function"]["name"], tc["function"]["arguments"])
                    messages.append({"role": "tool", "name": tc["function"]["name"], "content": "\n".join([c.text for c in res.content if hasattr(c, 'text')])})

    async def _chat_gemini(self, user_input: str) -> str:
        response = await asyncio.to_thread(self.gemini_model.generate_content, user_input)
        return response.text

# --- Main Bot Flow ---
bridge = None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.from_user: return
    if update.message.from_user.id != WHITE_LIST_ID: return
    try:
        response = await bridge.chat(update.message.text)
        await update.message.reply_text(response[:4000])
    except Exception as e:
        logger.exception("Chat Error")
        await update.message.reply_text(f"❌ Error: {str(e)}")

def maintain_models():
    print("🧹 Cleaning up models...")
    subprocess.run(["ollama", "rm", "gemma4:e4b"], capture_output=True)
    print("📥 Ensuring gemma3n:e2b is ready...")
    subprocess.run(["ollama", "pull", "gemma3n:e2b"], capture_output=True) 

if __name__ == '__main__':
    if not TOKEN or not GEMINI_API_KEY:
        print("❌ Error: Missing environment variables in .env file.")
        exit(1)

    print("--- Antigravity Mode Selection ---")
    print("1. Online Mode (Gemini 2.0 Flash Lite)")
    print("2. Offline Mode (Local Gemma 3n:e2b)")
    choice = input("Select mode (1/2): ").strip()
    
    if choice == '1':
        bridge = HybridBridge(mode='online')
    else:
        maintain_models()
        bridge = HybridBridge(mode='offline', local_model="gemma3n:e2b")
    
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    print(f"🚀 Bot starting in {'ONLINE' if choice=='1' else 'OFFLINE'} mode...")
    application.run_polling()
