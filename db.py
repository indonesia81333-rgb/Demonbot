import asyncio
import os
import sqlite3
import time

from config import DB_PATH

os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
_lock = asyncio.Lock()
_conn.executescript(
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        files INTEGER DEFAULT 0,
        bytes INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS files (
        token TEXT PRIMARY KEY,
        user_id INTEGER,
        key TEXT,
        name TEXT,
        size INTEGER,
        created REAL
    );
    """
)
_conn.commit()


async def _run(sql, args=(), fetch=False):
    async with _lock:
        def work():
            cur = _conn.execute(sql, args)
            rows = cur.fetchall() if fetch else None
            _conn.commit()
            return rows
        return await asyncio.to_thread(work)


async def add_usage(user_id, size):
    await _run(
        "INSERT INTO users(user_id, files, bytes) VALUES(?, 1, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET files=files+1, bytes=bytes+?",
        (user_id, size, size),
    )


async def totals():
    rows = await _run(
        "SELECT COUNT(*), COALESCE(SUM(files),0), COALESCE(SUM(bytes),0) FROM users",
        fetch=True,
    )
    return rows[0]


async def add_file(token, user_id, key, name, size):
    await _run(
        "INSERT INTO files(token, user_id, key, name, size, created) VALUES(?,?,?,?,?,?)",
        (token, user_id, key, name, size, time.time()),
    )


async def get_file(token):
    rows = await _run("SELECT key, name, size FROM files WHERE token=?", (token,), fetch=True)
    return rows[0] if rows else None


async def recent_files(user_id, limit=10):
    return await _run(
        "SELECT token, name, size FROM files WHERE user_id=? ORDER BY created DESC LIMIT ?",
        (user_id, limit),
        fetch=True,
    )
