import re
from urllib.parse import urlsplit

WEBSITES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "github": "https://github.com",
    "python": "https://www.python.org",
}


DISPLAY_NAMES = {"youtube": "YouTube", "google": "Google", "github": "GitHub", "python": "Python.org"}


def safe_url(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        raise ValueError("Only HTTPS URLs without embedded credentials are allowed.")
    if parts.hostname not in {"www.youtube.com", "www.google.com", "github.com", "www.python.org"}:
        raise ValueError("Website is not in the approved registry.")
    if any(ord(c) < 32 for c in url) or "\\" in url:
        raise ValueError("Invalid URL.")
    if parts.port not in (None, 443):
        raise ValueError("Only the standard HTTPS port is supported.")
    return url


def note_path(directory, title: str):
    if not re.fullmatch(r"[\w][\w -]{0,79}", title, flags=re.UNICODE):
        raise ValueError("Note title must be 1–80 letters, numbers, spaces, underscores or hyphens.")
    path = directory / (title + ".txt")
    if path.is_symlink() or path.resolve().parent != directory.resolve():
        raise ValueError("Note path escapes the application notes directory.")
    return path
