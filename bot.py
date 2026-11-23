import asyncio
import logging
import os
import time
import uuid
from urllib.parse import quote

from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

import config
import db
import filepress
import web

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("bot")

os.makedirs(config.DOWNLOAD_DIR, exist_ok=True)

bot = Client(
    "filepress_bot",
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
    "<b>Filepress Upload Bot</b>\n\n"
    "Send me any file, video, audio or photo and I'll upload it to Filepress "
    "and give you a download link.\n\n"
    "/connect &lt;api_key&gt; - connect your Filepress developer API key\n"
    "/mykey - show whether a key is connected\n"
    "/disconnect - remove your key\n"
    "/status - bot status and uptime\n"
    "/help - this message\n\n"
    "Limit: 2 GB per file (4 GB for the owner with a Premium session)."
)


def human(n):
    return web.fmt_size(n)


def media_of(msg: Message):
    for kind in ("document", "video", "audio", "voice", "animation", "video_note", "photo"):
        m = getattr(msg, kind, None)
        if m:
            return kind, m
    return None, None


@bot.on_message(filters.command(["start", "help"]) & filters.private)
async def start_cmd(_, msg: Message):
    await msg.reply_text(HELP)


@bot.on_message(filters.command("connect") & filters.private)
async def connect_cmd(_, msg: Message):
    if len(msg.command) < 2:
        return await msg.reply_text("Usage: <code>/connect YOUR_FILEPRESS_API_KEY</code>")
    key = msg.command[1].strip()
    await db.set_key(msg.from_user.id, key)
    try:
        await msg.delete()  # remove the message that contains the key
    except Exception:
        pass
    await bot.send_message(msg.chat.id, "Filepress API key connected. Now send me a file.")


@bot.on_message(filters.command("mykey") & filters.private)
async def mykey_cmd(_, msg: Message):
    key = await db.get_key(msg.from_user.id)
    if key:
        await msg.reply_text(f"Connected: <code>{key[:4]}...{key[-4:]}</code>")
    elif config.FILEPRESS_DEFAULT_KEY:
        await msg.reply_text("No personal key set; the bot's default key will be used.")
    else:
        await msg.reply_text("No key connected. Use /connect &lt;api_key&gt;.")


@bot.on_message(filters.command("disconnect") & filters.private)
async def disconnect_cmd(_, msg: Message):
    await db.del_key(msg.from_user.id)
    await msg.reply_text("API key removed.")


@bot.on_message(filters.command("status") & filters.private)
async def status_cmd(_, msg: Message):
    s = await web.snapshot()
    await msg.reply_text(
        f"<b>Status:</b> {s['status']}\n"
        f"<b>Uptime:</b> {s['uptime']}\n"
        f"<b>Active jobs:</b> {s['active_jobs']}\n"
        f"<b>Users:</b> {s['users']}\n"
        f"<b>Files:</b> {s['files']} ({s['size_human']})\n"
        f"<b>Filepress:</b> {'reachable' if s['filepress_reachable'] else 'unreachable'}\n"
        f"<b>Premium session:</b> {'on' if s['premium_session'] else 'off'}"
    )


def make_progress(status: Message, label: str):
    """Throttled progress updates. Must be a plain async function so Pyrogram awaits it."""
    last = [0.0]

    async def progress(current, total):
        now = time.time()
        if now - last[0] < 4 and current != total:
            return
        last[0] = now
        pct = current * 100 / total if total else 0
        try:
            await status.edit_text(f"{label}\n{human(current)} / {human(total)} ({pct:.0f}%)")
        except Exception:
            pass

    return progress


async def fetch_large_via_user(msg: Message, size: int, dest: str):
    """Owner-only: >2GB files are pulled with the Premium user session."""
    me = await bot.get_me()
    media_kind, media = media_of(msg)
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
    kind, media = media_of(msg)
    size = getattr(media, "file_size", 0) or 0
    name = getattr(media, "file_name", None) or f"{kind}_{msg.id}"
    if kind == "photo" and "." not in name:
        name += ".jpg"
    use_user = False

    if size > config.BOT_MAX_SIZE:
        if user_client and uid == config.OWNER_ID and size <= config.PREMIUM_MAX_SIZE:
            use_user = True
        else:
            return await msg.reply_text(
                f"File is {human(size)}. Limit is {human(config.BOT_MAX_SIZE)} for bots "
                f"(4 GB needs the owner's Premium session)."
            )

    key = await db.get_key(uid)
    if not key and not config.FILEPRESS_DEFAULT_KEY:
        return await msg.reply_text("Connect your key first: <code>/connect YOUR_API_KEY</code>")

    status = await msg.reply_text("Starting download...")
    work_dir = os.path.join(config.DOWNLOAD_DIR, uuid.uuid4().hex)
    os.makedirs(work_dir, exist_ok=True)
    dest = os.path.join(work_dir, name)
    web.state["processing"] += 1
    try:
        if use_user:
            await status.edit_text("Downloading via Premium session...")
            path = await fetch_large_via_user(msg, size, dest)
        else:
            path = await msg.download(file_name=dest, progress=make_progress(status, "Downloading..."))
        await status.edit_text(f"Uploading to Filepress... ({human(size)})")
        link = await filepress.upload(path, name, key)
        await db.add_usage(uid, size)

        share_url = f"https://t.me/share/url?url={quote(link)}&text={quote(name)}"
        kb = InlineKeyboardMarkup(
            [[
                InlineKeyboardButton("Download", url=link),
                InlineKeyboardButton("Share", url=share_url),
            ]]
        )
        await status.edit_text(
            f"<b>Uploaded</b>\n\n<b>Name:</b> <code>{name}</code>\n"
            f"<b>Size:</b> {human(size)}\n<b>Link:</b> {link}",
            reply_markup=kb,
            disable_web_page_preview=True,
        )
    except filepress.FilepressError as e:
        web.state["errors"] += 1
        await status.edit_text(f"Upload failed: {e}")
    except Exception as e:
        web.state["errors"] += 1
        log.exception("handler failed")
        await status.edit_text(f"Something went wrong: {e}")
    finally:
        web.state["processing"] -= 1
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
