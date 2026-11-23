import asyncio
import os
import sqlite3

from config import DB_PATH

os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
_lock = asyncio.Lock()
_conn.executescript(
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        api_key TEXT,
        files INTEGER DEFAULT 0,
        bytes INTEGER DEFAULT 0
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


async def set_key(user_id, key):
    await _run(
        "INSERT INTO users(user_id, api_key) VALUES(?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET api_key=excluded.api_key",
        (user_id, key),
    )


async def get_key(user_id):
    rows = await _run("SELECT api_key FROM users WHERE user_id=?", (user_id,), fetch=True)
    return rows[0][0] if rows and rows[0][0] else None


async def del_key(user_id):
    await _run("UPDATE users SET api_key=NULL WHERE user_id=?", (user_id,))


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
