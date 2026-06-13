import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(f"缺少必要的環境變數：{key}，請確認 .env 檔案設定正確。")
    return value


REDDIT_CLIENT_ID = _require("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = _require("REDDIT_CLIENT_SECRET")
GEMINI_API_KEY = _require("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = _require("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = _require("TELEGRAM_CHAT_ID")
