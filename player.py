"""Nova Media Player: media-type detection and rendering of the hosted player page."""
import html
import json
import re
from pathlib import Path

import config

SIGN_TTL = 6 * 3600  # lifetime of the signed playback URL embedded in the page

VIDEO = {"mp4", "m4v", "webm", "mov", "mkv", "avi", "ogv", "3gp", "ts"}
AUDIO = {"mp3", "m4a", "aac", "ogg", "oga", "opus", "wav", "flac", "weba"}
IMAGE = {"jpg", "jpeg", "png", "gif", "webp", "bmp", "svg"}

KIND_LABEL = {"video": "Video", "audio": "Audio", "image": "Image"}
BUTTON_LABEL = {
    "video": "▶️ Play online · Nova Player",
    "audio": "▶️ Play online · Nova Player",
    "image": "🖼 View online · Nova Player",
}

_TEMPLATE = Path(__file__).with_name("player.html").read_text(encoding="utf-8")
_PLACEHOLDER = re.compile(r"__(TITLE|DATA)__")


def kind_of(name):
    """Return 'video', 'audio', 'image' or None for a file name."""
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext in VIDEO:
        return "video"
    if ext in AUDIO:
        return "audio"
    if ext in IMAGE:
        return "image"
    return None


def player_url(token):
    """Public Nova Player URL for a file token, or None when no public app URL is configured."""
    if not config.APP_URL:
        return None
    return f"{config.APP_URL.rstrip('/')}/p/{token}"


def _json_for_script(data):
    # keep the JSON inert inside <script type="application/json">
    return (
        json.dumps(data, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace(" ", "\\u2028")
        .replace(" ", "\\u2029")
    )


def render(token, name, size_human, kind, src):
    """Render the player page. `src` is the signed inline URL the media element loads."""
    data = {
        "token": token,
        "name": name,
        "kind": kind,
        "kind_label": KIND_LABEL[kind],
        "size_human": size_human,
        "src": src,
        "stream": f"/s/{token}",
        "download": f"/d/{token}",
    }
    values ={"TITLE": html.escape(name, quote=True), "DATA": _json_for_script(data)}
    # single pass, so text inside an inserted value is never re-scanned for placeholders
    return _PLACEHOLDER.sub(lambda mo: values[mo.group(1)], _TEMPLATE)
