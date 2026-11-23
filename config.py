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

# --- Filepress ---
FILEPRESS_BASE_URL = os.getenv("FILEPRESS_BASE_URL", "https://new4.filepress.lat").rstrip("/")
# The upload endpoint path and auth header of your filepress account/API.
# Check your filepress developer/API page and adjust these three if they differ.
FILEPRESS_UPLOAD_PATH = os.getenv("FILEPRESS_UPLOAD_PATH", "/api/v1/file/upload")
FILEPRESS_AUTH_HEADER = os.getenv("FILEPRESS_AUTH_HEADER", "Authorization")
FILEPRESS_AUTH_PREFIX = os.getenv("FILEPRESS_AUTH_PREFIX", "Bearer ")
FILEPRESS_FILE_FIELD = os.getenv("FILEPRESS_FILE_FIELD", "file")
# Dotted path to the link inside the JSON response, e.g. "data.url". Falls back to first URL found.
FILEPRESS_LINK_FIELD = os.getenv("FILEPRESS_LINK_FIELD", "data.url")
# Used if a user hasn't connected their own key
FILEPRESS_DEFAULT_KEY = os.getenv("FILEPRESS_DEFAULT_KEY", "")

# --- Limits ---
BOT_MAX_SIZE = 2 * 1024**3        # MTProto bot download limit
PREMIUM_MAX_SIZE = 4 * 1024**3    # Premium user session limit
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")

# --- Web / Render ---
PORT = _int("PORT", 8080)
APP_URL = os.getenv("RENDER_EXTERNAL_URL", os.getenv("APP_URL", ""))
DB_PATH = os.getenv("DB_PATH", "data/bot.db")
