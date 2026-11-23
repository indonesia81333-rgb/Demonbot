import os
from dotenv import load_dotenv

load_dotenv()


def _int(name, default=0):
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


# --- Telegram ---
API_ID = _int("API_ID")
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = _int("OWNER_ID")
# Optional: Telegram Premium user session string (enables files up to 4GB for the owner)
USER_SESSION = os.getenv("USER_SESSION", "")

# --- Wasabi (S3-compatible) ---
WASABI_ACCESS_KEY = os.getenv("WASABI_ACCESS_KEY", "")
WASABI_SECRET_KEY = os.getenv("WASABI_SECRET_KEY", "")
WASABI_BUCKET = os.getenv("WASABI_BUCKET", "")
WASABI_REGION = os.getenv("WASABI_REGION", "us-east-1")
WASABI_ENDPOINT = os.getenv("WASABI_ENDPOINT", f"https://s3.{WASABI_REGION}.wasabisys.com")
WASABI_ENABLED = all([WASABI_ACCESS_KEY, WASABI_SECRET_KEY, WASABI_BUCKET])

# --- Limits ---
BOT_MAX_SIZE = 2 * 1024**3        # MTProto bot download limit
PREMIUM_MAX_SIZE = 4 * 1024**3    # Premium user session limit
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")

# --- Web / Render ---
PORT = _int("PORT", 8080)
APP_URL = os.getenv("RENDER_EXTERNAL_URL", os.getenv("APP_URL", ""))
DB_PATH = os.getenv("DB_PATH", "data/bot.db")
