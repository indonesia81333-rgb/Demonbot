# Wasabi Telegram Upload Bot

Send any file to the bot; it uploads it to your Wasabi bucket and replies with **Download** and **Share** buttons.

## Features
- Wasabi (S3-compatible) multipart uploads, parallel and fast
- Real-time progress in Telegram (bar, speed, ETA) for both download and upload
- Permanent bot-hosted links (`/d/<token>`) that redirect to a fresh signed Wasabi URL each time
- Animated live dashboard at `/` (uptime, users, files, data, live transfer progress), JSON at `/api/status`, health check at `/health`
- Up to 2 GB per file; 4 GB for the owner with a Telegram Premium session
- Dockerfile and `render.yaml` for Render

## Environment variables
| Name | Purpose |
|---|---|
| `API_ID`, `API_HASH` | from https://my.telegram.org |
| `BOT_TOKEN` | from @BotFather |
| `OWNER_ID` | your Telegram user id |
| `WASABI_ACCESS_KEY` / `WASABI_SECRET_KEY` | Wasabi access keys |
| `WASABI_BUCKET` | bucket name |
| `WASABI_REGION` | bucket region, e.g. `us-east-1`, `ap-southeast-1` |
| `WASABI_ENDPOINT` | optional override; default `https://s3.<region>.wasabisys.com` |
| `USER_SESSION` | optional Premium session string for 4 GB owner uploads |

## Run locally
```
pip install -r requirements.txt
python bot.py
```

## Deploy on Render
1. Push this folder to GitHub, then Render > New > Blueprint.
2. Fill the secret env vars. Render sets `RENDER_EXTERNAL_URL`, which is used to build the permanent download links.
3. The free plan can sleep; use a paid instance or an uptime monitor on `/health`.
4. Attach a persistent disk at `/app/data`, or the file-link database is lost on redeploy and old `/d/` links stop working.

## Notes
- Without `RENDER_EXTERNAL_URL`/`APP_URL`, links are direct signed Wasabi URLs that expire after 7 days (the S3 maximum).
- The dashboard is public and never shows file names.
- The bucket should stay private; the bot serves files through signed URLs.
- Render needs enough disk for the largest file, since files are staged locally before upload.
