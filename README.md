# Wasabi Telegram Upload Bot

Send a file to the Telegram bot. The bot uploads it to a private Wasabi bucket and replies with **Download** and **Share** buttons, plus a **Play** button (Nova Media Player) for video, audio and images.

This package includes a premium, animated dashboard front end for the bot's existing `/` page. It is a dashboard add-on; it does not replace the Telegram bot, storage client, transfer engine, database, or signed-link backend.

## Core bot features

- Wasabi S3-compatible multipart uploads with parallel transfer support.
- Real-time Telegram progress updates with progress bar, transfer speed, and ETA for uploads and downloads.
- Permanent bot-hosted download links at `/d/<token>` that redirect to a newly generated signed Wasabi URL.
- **Nova Media Player** at `/p/<token>`: stream video, audio and images online, with Download and Play buttons (see below).
- Public aggregate dashboard at `/`, JSON status API at `/api/status`, and health check at `/health`.
- Project README configuration: up to 2 GB per file, or up to 4 GB for the owner when using a Telegram Premium session. Actual limits depend on the bot configuration and Telegram account/session capabilities.
- Dockerfile and `render.yaml` deployment configuration.

## Nova Media Player (online player)

Videos, audio files and images uploaded to the bot can be played or viewed straight in the browser, without downloading them first.

After an upload the bot replies with:

| Button | What it does |
|---|---|
| **▶️ Play online · Nova Player** | Opens the hosted player page at `/p/<token>` (shown for video, audio and image files) |
| **Download** | Permanent download link at `/d/<token>` |
| **Share** | Telegram share sheet for the download link |

The player page includes:

- Streaming with seeking (the bucket serves HTTP Range requests on signed URLs), buffered-range display, and a loading spinner.
- Play/pause, ±10 s skip, playback speed (0.5×–2×), loop, volume and mute, picture-in-picture, and fullscreen.
- Keyboard shortcuts: `Space`/`K` play-pause, `←`/`→` seek 5 s, `J`/`L` seek 10 s, `↑`/`↓` volume, `M` mute, `F` fullscreen, `0`–`9` jump to 0–90 %.
- Resume from the last position (stored per file in the browser) and remembered volume.
- A **Download** button, a **Copy stream link** button (paste it into VLC or MX Player as a network stream), and a friendly fallback with Download/Reload if the browser can't decode the format.
- Audio gets an animated cover; images get a click-to-zoom viewer.

Routes added:

| Route | Purpose |
|---|---|
| `GET /p/<token>` | Nova Media Player page. Non-playable file types redirect to `/d/<token>`. |
| `GET /s/<token>` | Stable stream link; redirects to a fresh inline signed URL (use it in external players). |

Notes:

- The player is served by the bot's web app, so it needs a public base URL: set `APP_URL`, or deploy on Render, which provides `RENDER_EXTERNAL_URL`. Without one, uploads keep working but no Play button is shown.
- The bucket stays private. The page embeds a signed URL that is valid for 6 hours; `/s/<token>` always issues a new one. Player and stream responses are sent with `Cache-Control: no-store` and `Referrer-Policy: no-referrer`.
- Playback depends on the browser's codecs. MP4 (H.264/AAC), WebM, MP3, AAC/M4A, OGG/Opus and WAV work almost everywhere; MKV, AVI and FLAC vary by browser, so the page offers Download and the stream link as a fallback.
- `/myfiles` also lists a **▶ Play** link next to playable files.

## Dashboard design upgrade

The replacement page is named **Wasabi Transfer Center** and uses a premium **Aurora / Obsidian** design direction.

### Visual experience

- Deep navy background with soft aurora lighting and animated ambient glow.
- Frosted-glass cards, subtle borders, depth shadows, and high-contrast typography.
- Smooth page entrance, status pulse, animated transfer progress, and shimmer effects.
- Dark and light theme switch.
- Teal, violet, and blue accent palettes.
- Responsive desktop, tablet, and mobile layout.
- Focus-visible keyboard controls and device-level reduced-motion support.

### Dashboard modules

- **System overview:** uptime, registered users, stored files, and transferred data.
- **Transfer monitor:** active uploads and downloads, progress percentage, status, speed, and ETA.
- **Service health:** `/api/status` and `/health` connectivity with response timing.
- **Appearance studio:** saved theme and accent preferences.
- **Privacy-first display:** the dashboard does not render file names, object keys, Telegram user IDs, tokens, or credentials.

### Included files

```text
wasabi-dashboard-addon/
├── README.md
├── INTEGRATION.md
└── templates/
    └── index.html
```

## Install the dashboard

1. Copy `templates/index.html` into the bot repository's `templates/` directory.
2. Replace the old dashboard template; do not add a duplicate root route.
3. Keep the existing `/api/status` and `/health` endpoints.
4. Ensure the root route renders `index.html`.
5. Deploy the updated repository and open the service root URL.

For a Flask application, the route should look similar to this **only if a root route does not already exist**:

```python
from flask import render_template

@app.get("/")
def dashboard():
    return render_template("index.html")
```

The HTML is self-contained and does not require a frontend build step or JavaScript animation framework. DM Sans and Manrope are loaded from Google Fonts; system sans-serif fonts are used as fallbacks if the fonts cannot be reached.

## Status API contract

The page refreshes `GET /api/status` every 10 seconds and checks `GET /health`. For the full dashboard, return aggregate data in a structure similar to:

```json
{
  "uptime_seconds": 86400,
  "users": 125,
  "files": 820,
  "data_transferred": 9876543210,
  "active_uploads": 1,
  "active_downloads": 0,
  "transfers": [
    {
      "type": "upload",
      "progress": 64,
      "speed": 5242880,
      "eta": 42,
      "status": "uploading"
    }
  ]
}
```

| Field | Meaning | Display behavior |
|---|---|---|
| `uptime_seconds` | Seconds since the bot process started | Converted to days, hours, minutes, and seconds |
| `users` | Total known bot users | Formatted count |
| `files` | Total stored file records or links | Formatted count |
| `data_transferred` | Total transferred bytes | Formatted as B, KB, MB, GB, TB, or PB |
| `active_uploads` | Current upload count | Integer count |
| `active_downloads` | Current download count | Integer count |
| `transfers` | Optional list of live transfers | Progress, speed, ETA, and status |

Each item in `transfers` can contain:

- `type`: `upload` or `download`.
- `progress`: number from 0 to 100.
- `speed`: bytes per second.
- `eta`: remaining seconds or a preformatted text value.
- `status`: a short status such as `uploading` or `downloading`.

The frontend also recognizes common aliases such as `total_users`, `total_files`, `total_bytes`, `active_transfers`, `direction`, `percent`, `bytes_per_second`, and `state`. Missing values appear as an em dash; the page does not invent statistics. If the backend uses another JSON shape, adjust `getMetric()` and `normalizeTransfers()` in `templates/index.html` to match it.

## Environment variables

Set these values in the deployment environment. Do not commit real credentials to GitHub.

| Name | Purpose |
|---|---|
| `API_ID`, `API_HASH` | Telegram API credentials from [my.telegram.org](https://my.telegram.org) |
| `BOT_TOKEN` | Bot token from [@BotFather](https://t.me/BotFather) |
| `OWNER_ID` | Telegram numeric user ID of the owner |
| `WASABI_ACCESS_KEY` / `WASABI_SECRET_KEY` | Wasabi access credentials |
| `WASABI_BUCKET` | Private bucket name |
| `WASABI_REGION` | Bucket region, e.g. `us-east-1` or `ap-southeast-1` |
| `WASABI_ENDPOINT` | Optional endpoint override; default depends on the configured region |
| `USER_SESSION` | Optional Telegram Premium session string for the owner upload path |
| `APP_URL` | Optional public application base URL when not using Render's external URL |
| `RENDER_EXTERNAL_URL` | Set by Render and used to construct permanent bot-hosted links |

## Run locally

```bash
pip install -r requirements.txt
python bot.py
```

The dashboard template expects the bot's web application to serve the root path and the two status endpoints on the same origin.

## Deploy on Render

1. Push the bot repository to GitHub.
2. In Render, choose **New → Blueprint** and select the repository containing `render.yaml`.
3. Set the secret environment variables in the Render dashboard.
4. Confirm the service has the correct web process, port binding, and health-check path (`/health`).
5. Attach persistent storage at `/app/data` for the file-link database if the deployment plan supports it.
6. Deploy, then check `/`, `/api/status`, and `/health`.

Render services use an ephemeral filesystem by default. Persistent disks preserve filesystem changes across deploys and restarts; Render's current documentation states that persistent disks are available for paid web services, private services, and background workers. Confirm the plan and mount path in the Render dashboard before relying on local database persistence.

The free plan may sleep. A sleeping service can delay bot responses until it wakes. An uptime monitor does not guarantee that a free instance remains continuously available; choose a suitable deployment plan for production use.

## Link, storage, and security notes

- Keep the Wasabi bucket private. The bot should issue time-limited signed URLs rather than expose permanent public bucket access.
- The `/d/<token>` route is the stable application link; it can redirect to a fresh signed URL when a user opens it.
- Wasabi documents presigned URLs as temporary access links and describes a duration range of 12 hours to 7 days for the documented workflow. A signed URL expires; the permanent bot-hosted redirect is the layer that can generate a fresh one.
- Multipart uploads split a large object into parts and reassemble it when the upload completes. Incomplete multipart uploads are cleaned up by Wasabi after approximately 31 days according to its multipart upload guidance.
- Keep Telegram tokens, API hashes, Wasabi keys, session strings, signed URLs, and private object keys on the server. Never embed them in HTML or `/api/status`.
- Expose aggregate counts and transfer telemetry only. Do not expose file names, Telegram user IDs, or private object metadata on the public dashboard.
- The dashboard is a front-end display only. It does not change upload concurrency, file-size limits, Telegram MTProto behavior, Wasabi permissions, link generation, or database persistence.

## Online documentation and design references

- [Wasabi API Reference Center](https://docs.wasabi.com/apidocs): Wasabi API overview and S3 API access.
- [Wasabi multipart upload guide](https://docs.wasabi.com/docs/how-does-wasabi-handle-multipart-uploads): multipart behavior and parallel/part-based uploads.
- [Wasabi presigned URLs guide](https://docs.wasabi.com/docs/how-do-i-generate-pre-signed-urls-for-temporary-access-with-wasabi): temporary signed access and expiration behavior.
- [Render Web Services](https://render.com/docs/web-services): service deployment and configuration.
- [Render Health Checks](https://render.com/docs/health-checks): HTTP health-check path configuration.
- [Render Persistent Disks](https://render.com/docs/disks): persistence across deploys and restarts.
- [MDN `prefers-reduced-motion`](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/%40media) and [W3C WAI reduced-motion technique](https://www.w3.org/WAI/WCAG22/Techniques/css/C39.html): accessibility guidance for reducing non-essential animation.
- [Google Fonts — DM Sans](https://fonts.google.com/specimen/DM+Sans) and [Manrope](https://fonts.google.com/specimen/Manrope): the optional dashboard font families.

## Troubleshooting the dashboard

- **All metrics show `—`:** open `/api/status` directly and compare its JSON field names with the status API contract above.
- **Dashboard says connection issue:** verify `/api/status` returns HTTP 200 JSON and that the web service is running.
- **Health check shows unavailable:** verify `/health` returns HTTP 200 without requiring Telegram authentication.
- **Theme resets:** browser storage may be disabled or cleared; preferences are local to each browser.
- **Fonts look different:** Google Fonts may be blocked; the page automatically falls back to system fonts.
- **Old links disappear after redeploy:** check the database path and persistent disk mount. The original project notes that its link database must be persisted for stable `/d/` records.
