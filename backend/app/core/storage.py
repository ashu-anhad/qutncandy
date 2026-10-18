"""File storage seam. Local disk today; swap these two functions for S3/R2 later."""
import uuid
from pathlib import Path

from .config import settings


def save_file(data: bytes, folder: str, ext: str) -> str:
    """Store bytes and return the public URL."""
    name = f"{uuid.uuid4().hex}.{ext.lstrip('.')}"
    target = Path(settings.media_dir) / folder
    target.mkdir(parents=True, exist_ok=True)
    (target / name).write_bytes(data)
    return f"{settings.media_url}/{folder}/{name}"


def delete_file(url: str) -> None:
    if not url.startswith(settings.media_url + "/"):
        return
    path = Path(settings.media_dir) / url.removeprefix(settings.media_url + "/")
    path.unlink(missing_ok=True)
