import aiohttp

import config


class FilepressError(Exception):
    pass


def _dig(data, path):
    for part in path.split("."):
        if isinstance(data, dict) and part in data:
            data = data[part]
        else:
            return None
    return data if isinstance(data, str) else None


def _first_url(data):
    if isinstance(data, str) and data.startswith("http"):
        return data
    if isinstance(data, dict):
        for v in data.values():
            found = _first_url(v)
            if found:
                return found
    if isinstance(data, list):
        for v in data:
            found = _first_url(v)
            if found:
                return found
    return None


async def upload(path, filename, api_key):
    """Upload a local file to filepress and return the share/download link."""
    api_key = api_key or config.FILEPRESS_DEFAULT_KEY
    if not api_key:
        raise FilepressError("No filepress API key connected. Use /connect <key>.")

    url = config.FILEPRESS_BASE_URL + config.FILEPRESS_UPLOAD_PATH
    headers, params = {}, {}
    mode = config.FILEPRESS_AUTH_MODE
    if mode == "header":
        headers[config.FILEPRESS_AUTH_HEADER] = config.FILEPRESS_AUTH_PREFIX + api_key
    elif mode == "query":
        params[config.FILEPRESS_AUTH_PARAM] = api_key
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=30)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        with open(path, "rb") as fh:
            form = aiohttp.FormData()
            if mode == "form":
                form.add_field(config.FILEPRESS_AUTH_PARAM, api_key)
            form.add_field(config.FILEPRESS_FILE_FIELD, fh, filename=filename)
            async with session.post(url, data=form, headers=headers, params=params) as resp:
                text = await resp.text()
                if resp.status in (401, 403):
                    raise FilepressError(f"Filepress rejected the key ({resp.status}): {text[:200]}")
                if resp.status >= 400:
                    raise FilepressError(f"Filepress error {resp.status}: {text[:200]}")
                try:
                    payload = await resp.json(content_type=None)
                except Exception:
                    raise FilepressError(f"Unexpected response: {text[:200]}")

    link = _dig(payload, config.FILEPRESS_LINK_FIELD) or _first_url(payload)
    if not link:
        raise FilepressError(f"No link found in response: {str(payload)[:200]}")
    return link


async def check_key(api_key):
    """Cheap reachability check of the filepress host (used by the dashboard)."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
            async with s.get(config.FILEPRESS_BASE_URL) as r:
                return r.status < 500
    except Exception:
        return False
