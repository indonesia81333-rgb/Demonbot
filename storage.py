import asyncio
import mimetypes
import re
import threading
import time
from urllib.parse import quote

import boto3
from boto3.s3.transfer import TransferConfig
from botocore.config import Config

import config

MAX_PRESIGN = 7 * 24 * 3600  # S3 presigned URLs cannot exceed 7 days

_client = None


def enabled():
    return config.WASABI_ENABLED


def client():
    global _client
    if _client is None:
        _client = boto3.client(
            "s3",
            endpoint_url=config.WASABI_ENDPOINT,
            aws_access_key_id=config.WASABI_ACCESS_KEY,
            aws_secret_access_key=config.WASABI_SECRET_KEY,
            region_name=config.WASABI_REGION,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
                retries={"max_attempts": 5, "mode": "standard"},
            ),
        )
    return _client


async def upload(path, key, size, progress_cb):
    """Multipart upload to Wasabi in a worker thread with throttled async progress."""
    loop = asyncio.get_running_loop()
    sent = 0
    lock = threading.Lock()
    last = [0.0]

    def cb(n):
        nonlocal sent
        with lock:
            sent += n
            cur = sent
        now = time.time()
        if now - last[0] >= 1.5 or cur >= size:
            last[0] = now
            asyncio.run_coroutine_threadsafe(progress_cb(min(cur, size), size), loop)

    extra = {}
    ctype = mimetypes.guess_type(key)[0]
    if ctype:
        extra["ContentType"] = ctype
    cfg = TransferConfig(
        multipart_threshold=64 * 1024**2,
        multipart_chunksize=64 * 1024**2,
        max_concurrency=8,
        use_threads=True,
    )

    def work():
        client().upload_file(path, config.WASABI_BUCKET, key, ExtraArgs=extra or None, Callback=cb, Config=cfg)

    await asyncio.to_thread(work)


def presign(key, filename, expires=3600):
    safe = filename.replace('"', "").replace("\\", "").replace("\n", " ")
    return client().generate_presigned_url(
        "get_object",
        Params={
            "Bucket": config.WASABI_BUCKET,
            "Key": key,
            "ResponseContentDisposition": f'attachment; filename="{safe}"',
        },
        ExpiresIn=min(expires, MAX_PRESIGN),
    )


_CTYPES = {
    ".mkv": "video/x-matroska",
    ".mov": "video/quicktime",
    ".m4v": "video/mp4",
    ".m4a": "audio/mp4",
    ".opus": "audio/ogg",
    ".oga": "audio/ogg",
    ".flac": "audio/flac",
    ".weba": "audio/webm",
}


def _ctype(filename):
    ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""
    return _CTYPES.get(ext) or mimetypes.guess_type(filename)[0]


def presign_inline(key, filename, expires=6 * 3600):
    """Signed URL for in-browser playback (Content-Disposition: inline).

    S3-compatible storage answers HTTP Range requests on signed URLs, so
    <video>/<audio> elements can seek without downloading the whole file.
    """
    ascii_name = re.sub(r'[\x00-\x1f"\\]', "", filename.encode("ascii", "ignore").decode()).strip() or "file"
    params = {
        "Bucket": config.WASABI_BUCKET,
        "Key": key,
        "ResponseContentDisposition": f"inline; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}",
    }
    ctype = _ctype(filename)
    if ctype:
        params["ResponseContentType"] = ctype
    return client().generate_presigned_url("get_object", Params=params, ExpiresIn=min(expires, MAX_PRESIGN))


async def head_ok():
    """Reachability/credentials check for the dashboard."""
    try:
        await asyncio.to_thread(client().head_bucket, Bucket=config.WASABI_BUCKET)
        return True
    except Exception:
        return False
