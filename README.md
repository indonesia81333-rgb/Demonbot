# Filepress Telegram Bot

Telegram bot that takes any file you send, uploads it to filepress using your own
developer API key, and replies with **Download** and **Share** buttons.

## Features
- Upload via your personal Filepress API key (`/connect <key>`), stored per user
- Download link + Share button on every result
- Live download progress, automatic temp-file cleanup
- Up to 2 GB per file; 4 GB for the owner with a Telegram Premium session
- Web dashboard at `/` (status, uptime, users, files, data transferred), JSON at `/api/status`, health check at `/health`
- Self-ping keep-alive, Dockerfile and `render.yaml` for Render

## Setup
1. Get `API_ID` and `API_HASH` from https://my.telegram.org and a `BOT_TOKEN` from @BotFather.
2. Copy `.env.example` to `.env` and fill it in.
3. **Check your filepress API docs** and set `FILEPRESS_UPLOAD_PATH`, `FILEPRESS_AUTH_HEADER`,
   `FILEPRESS_AUTH_PREFIX`, `FILEPRESS_FILE_FIELD` and `FILEPRESS_LINK_FIELD` to match.
   These defaults are placeholders; the bot was written without access to that API's documentation.
4. Run locally:
   ```
   pip install -r requirements.txt
   python bot.py
   ```
   Dashboard: http://localhost:8080

## Deploy on Render
1. Push this folder to a GitHub repo.
2. Render > New > Blueprint (or Web Service with Docker) > select the repo.
3. Fill the secret env vars (`API_ID`, `API_HASH`, `BOT_TOKEN`, `OWNER_ID`).
4. Render sets `RENDER_EXTERNAL_URL` automatically; the bot pings `/health` every 10 min.
   The free plan can still sleep; use a paid instance or an external uptime monitor (e.g. UptimeRobot on `/health`) for true non-stop running.
5. SQLite data is lost on redeploy unless you attach a persistent disk mounted at `/app/data`.

## File size limits
- Bot accounts can download up to 2 GB over MTProto.
- 4 GB works only for the owner: set `USER_SESSION` (Pyrogram session string of a Premium account), `OWNER_ID`, and send the file from that account to the bot. The bot finds it in that account's chat history and downloads it with the Premium session.
- Render free disk is small and ephemeral, so very large files need enough disk on your plan.

## Commands
`/start` `/help` `/connect <key>` `/mykey` `/disconnect` `/status`

## Security
Keys are stored in plain text in SQLite. Protect the disk, or add encryption before opening the bot to the public.
