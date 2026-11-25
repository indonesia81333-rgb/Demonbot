import asyncio
import html
import logging
import mimetypes
import os
import re
import secrets
import time
import uuid
from urllib.parse import quote

from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

import config
import db
import player
import storage
import web

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("bot")

os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)

bot = Client(
    "wasabi_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
    in_memory=True,
)
user_client = None
if config.USER_SESSION:
    user_client = Client(
        "owner_user",
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        session_string=config.USER_SESSION,
        in_memory=True,
    )

HELP = (
    "<b>Cloud Upload Bot</b>\n\n"
    "Send me any file, video, audio or photo. I'll store it on Wasabi cloud "
    "storage and give you Download and Share buttons. Videos, audio and images "
    "also get a Play button that opens the Nova Media Player in your browser.\n\n"
    "/myfiles - your latest uploads\n"
    "/status - bot status and uptime\n"
    "/help - this message\n\n"
    "Limit: 2 GB per file (4 GB for the owner with a Premium session)."
)


def human(n):
    return web.fmt_size(n)


def bar(pct, n=14):
    filled = int(n * pct / 100)
    return "▰" * filled + "▱" * (n - filled)


def fmt_eta(sec):
    sec = int(sec)
    if sec <= 0:
        return "--"
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    return f"{h}h {m}m" if h else (f"{m}m {s}s" if m else f"{s}s")


def media_of(msg: Message):
    for kind in ("document", "video", "audio", "voice", "animation", "video_note", "photo"):
        m = getattr(msg, kind, None)
        if m:
            return kind, m
    return None, None


def safe_name(name):
    return re.sub(r"[\\/\x00-\x1f]", "_", name).strip() or "file"


def link_for(token, key, name):
    if config.APP_URL:
        return f"{config.APP_URL.rstrip('/')}/d/{token}"
    return storage.presign(key, name, storage.MAX_PRESIGN)  # 7 days max without a public app URL


def make_progress(status: Message, label: str, job: dict):
    """Live progress. Must be a plain async function so Pyrogram awaits it."""
    last = [0.0]
    t0 = time.time()

    async def progress(current, total):
        now = time.time()
        pct = current * 100 / total if total else 0
        job.update(stage=label, pct=round(pct, 1))
        if now - last[0] < 3 and current != total:
            return
        last[0] = now
        speed = current / max(now - t0, 0.001)
        eta = (total - current) / speed if speed and total else 0
        try:
            await status.edit_text(
                f"<b>{label}</b>\n<code>{bar(pct)}</code> {pct:.0f}%\n"
                f"{human(current)} / {human(total)}\n"
                f"Speed {human(speed)}/s · ETA {fmt_eta(eta)}"
            )
        except Exception:
            pass

    return progress


@bot.on_message(filters.command(["start", "help"]) & filters.private)
async def start_cmd(_, msg: Message):
    await msg.reply_text(HELP)


@bot.on_message(filters.command("status") & filters.private)
async def status_cmd(_, msg: Message):
    s = await web.snapshot()
    await msg.reply_text(
        f"<b>Status:</b> {s['status']}\n"
        f"<b>Uptime:</b> {s['uptime']}\n"
        f"<b>Active transfers:</b> {s['active_jobs']}\n"
        f"<b>Users:</b> {s['users']}\n"
        f"<b>Files:</b> {s['files']} ({s['size_human']})\n"
        f"<b>Wasabi:</b> {'connected' if s['backend_ok'] else 'unreachable'}\n"
        f"<b>Premium session:</b> {'on' if s['premium_session'] else 'off'}"
    )


@bot.on_message(filters.command("myfiles") & filters.private)
async def myfiles_cmd(_, msg: Message):
    rows = await db.recent_files(msg.from_user.id, 10)
    if not rows:
        return await msg.reply_text("No uploads yet. Send me a file!")
    lines = []
    for token, name, size in rows:
        url = f"{config.APP_URL.rstrip('/')}/d/{token}" if config.APP_URL else None
        safe = html.escape(name)
        line = f'• <a href="{url}">{safe}</a> ({human(size)})' if url else f"• {safe} ({human(size)})"
        play = player.player_url(token) if player.kind_of(name) else None
        if play:
            line += f' · <a href="{play}">▶ Play</a>'
        lines.append(line)
    await msg.reply_text("<b>Your latest files</b>\n" + "\n".join(lines), disable_web_page_preview=True)


async def fetch_large_via_user(msg: Message, dest: str):
    """Owner-only: >2GB files are pulled with the Premium user session."""
    me = await bot.get_me()
    _, media = media_of(msg)
    async for m in user_client.get_chat_history(me.username, limit=20):
        _, um = media_of(m)
        if um and um.file_unique_id == media.file_unique_id:
            return await user_client.download_media(m, file_name=dest)
    raise RuntimeError("Couldn't find the file in the owner's chat with the bot.")


@bot.on_message(
    (filters.document | filters.video | filters.audio | filters.voice
     | filters.animation | filters.video_note | filters.photo) & filters.private
)
async def handle_file(_, msg: Message):
    uid = msg.from_user.id
    if not storage.enabled():
        return await msg.reply_text("Storage isn't configured. The owner must set the WASABI_* variables.")

    kind, media = media_of(msg)
    size = getattr(media, "file_size", 0) or 0
    name = safe_name(getattr(media, "file_name", None) or f"{kind}_{msg.id}")
    if "." not in name:
        ext = mimetypes.guess_extension(getattr(media, "mime_type", "") or "") or (".jpg" if kind == "photo" else "")
        name += ext
    use_user = False

    if size > config.BOT_MAX_SIZE:
        if user_client and uid == config.OWNER_ID and size <= config.PREMIUM_MAX_SIZE:
            use_user = True
        else:
            return await msg.reply_text(
                f"File is {human(size)}. Limit is {human(config.BOT_MAX_SIZE)} for bots "
                f"(4 GB needs the owner's Premium session)."
            )

    status = await msg.reply_text("Starting...")
    work_dir = os.path.join(config.DOWNLOAD_DIR, uuid.uuid4().hex)
    os.makedirs(work_dir, exist_ok=True)
    dest = os.path.join(work_dir, name)
    job_id = uuid.uuid4().hex
    job = {"stage": "Queued", "pct": 0}
    web.state["jobs"][job_id] = job
    try:
        if use_user:
            await status.edit_text("Downloading via Premium session...")
            path = await fetch_large_via_user(msg, dest)
        else:
            path = await msg.download(file_name=dest, progress=make_progress(status, "Downloading from Telegram", job))
        real_size = os.path.getsize(path)

        key = f"{uid}/{uuid.uuid4().hex[:8]}/{name}"
        await storage.upload(path, key, real_size, make_progress(status, "Uploading to Wasabi", job))

        token = secrets.token_urlsafe(8)
        await db.add_file(token, uid, key, name, real_size)
        await db.add_usage(uid, real_size)
        link = link_for(token, key, name)

        share_url = f"https://t.me/share/url?url={quote(link)}&text={quote(name)}"
        # Nova Media Player needs the bot-hosted web app (APP_URL / RENDER_EXTERNAL_URL)
        play_url = player.player_url(token)
        play_kind = player.kind_of(name)
        rows = []
        if play_url and play_kind:
            rows.append([InlineKeyboardButton(player.BUTTON_LABEL[play_kind], url=play_url)])
        rows.append([
            InlineKeyboardButton("Download", url=link),
            InlineKeyboardButton("Share", url=share_url),
        ])
        kb = InlineKeyboardMarkup(rows)
        player_line = f"\n<b>Player:</b> {play_url}" if play_url and play_kind else ""
        await status.edit_text(
            f"<b>Upload complete</b>\n<code>{bar(100)}</code> 100%\n\n"
            f"<b>Name:</b> <code>{name}</code>\n<b>Size:</b> {human(real_size)}\n<b>Link:</b> {link}{player_line}",
            reply_markup=kb,
            disable_web_page_preview=True,
        )
    except Exception as e:
        web.state["errors"] += 1
        log.exception("handler failed")
        await status.edit_text(f"Upload failed: {e}")
    finally:
        web.state["jobs"].pop(job_id, None)
        try:
            for f in os.listdir(work_dir):
                os.remove(os.path.join(work_dir, f))
            os.rmdir(work_dir)
        except Exception:
            pass


async def main():
    runner = await web.start_web()
    await bot.start()
    web.state["bot_connected"] = True
    if user_client:
        await user_client.start()
        web.state["user_connected"] = True
    log.info("Bot started")
    try:
        await idle()
    finally:
        web.state["bot_connected"] = False
        await bot.stop()
        if user_client:
            await user_client.stop()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
