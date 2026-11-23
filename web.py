import asyncio
import time
from datetime import datetime, timezone

import aiohttp
from aiohttp import web

import config
import db
import filepress

STARTED = time.time()
state = {"bot_connected": False, "user_connected": False, "processing": 0, "errors": 0}


def fmt_uptime(sec):
    sec = int(sec)
    d, sec = divmod(sec, 86400)
    h, sec = divmod(sec, 3600)
    m, s = divmod(sec, 60)
    return f"{d}d {h}h {m}m {s}s"


def fmt_size(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.2f} {unit}"
        n /= 1024
    return f"{n:.2f} PB"


async def snapshot():
    users, files, size = await db.totals()
    fp_ok = await filepress.check_key(None)
    return {
        "status": "running" if state["bot_connected"] else "connecting",
        "uptime": fmt_uptime(time.time() - STARTED),
        "started": datetime.fromtimestamp(STARTED, timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "filepress_reachable": fp_ok,
        "premium_session": state["user_connected"],
        "active_jobs": state["processing"],
        "errors": state["errors"],
        "users": users,
        "files": files,
        "bytes": size,
        "size_human": fmt_size(size),
    }


PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="15"><title>Filepress Bot Dashboard</title>
<style>
body{{font-family:system-ui,sans-serif;background:#0f1115;color:#e8eaed;margin:0;padding:24px}}
.wrap{{max-width:720px;margin:auto}} h1{{font-size:22px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}}
.card{{background:#181b22;border:1px solid #262a33;border-radius:12px;padding:16px}}
.k{{font-size:12px;color:#8b93a1;text-transform:uppercase;letter-spacing:.05em}}
.v{{font-size:20px;margin-top:6px}} .ok{{color:#4ade80}} .bad{{color:#f87171}}
</style></head><body><div class="wrap">
<h1>Filepress Telegram Bot</h1>
<div class="grid">
<div class="card"><div class="k">Status</div><div class="v {sc}">{status}</div></div>
<div class="card"><div class="k">Uptime</div><div class="v">{uptime}</div></div>
<div class="card"><div class="k">Started</div><div class="v" style="font-size:14px">{started}</div></div>
<div class="card"><div class="k">Filepress</div><div class="v {fc}">{fp}</div></div>
<div class="card"><div class="k">Premium (4GB) session</div><div class="v">{prem}</div></div>
<div class="card"><div class="k">Active jobs</div><div class="v">{active_jobs}</div></div>
<div class="card"><div class="k">Users</div><div class="v">{users}</div></div>
<div class="card"><div class="k">Files processed</div><div class="v">{files}</div></div>
<div class="card"><div class="k">Data transferred</div><div class="v">{size_human}</div></div>
</div></div></body></html>"""


async def index(request):
    s = await snapshot()
    html = PAGE.format(
        sc="ok" if s["status"] == "running" else "bad",
        status=s["status"].upper(),
        uptime=s["uptime"],
        started=s["started"],
        fc="ok" if s["filepress_reachable"] else "bad",
        fp="Reachable" if s["filepress_reachable"] else "Unreachable",
        prem="Active" if s["premium_session"] else "Off",
        active_jobs=s["active_jobs"],
        users=s["users"],
        files=s["files"],
        size_human=s["size_human"],
    )
    return web.Response(text=html, content_type="text/html")


async def api_status(request):
    return web.json_response(await snapshot())


async def health(request):
    return web.Response(text="ok")


async def keep_alive():
    """Self-ping so Render-style hosts that sleep on idle stay awake."""
    if not config.APP_URL:
        return
    while True:
        await asyncio.sleep(600)
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as s:
                await s.get(config.APP_URL.rstrip("/") + "/health")
        except Exception:
            pass


async def start_web():
    app = web.Application()
    app.add_routes([web.get("/", index), web.get("/api/status", api_status), web.get("/health", health)])
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", config.PORT).start()
    asyncio.create_task(keep_alive())
    return runner
