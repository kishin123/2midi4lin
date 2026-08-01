import os

def _get_download_dir():
    """统一下载目录：~/Music/2midi4lin/downloads（打包后不依赖临时目录）。"""
    home = os.path.expanduser("~")
    d = os.path.join(home, "Music", "2midi4lin", "downloads")
    try:
        os.makedirs(d, exist_ok=True)
        return d
    except Exception:
        fallback = os.path.join(home, "2midi4lin", "downloads")
        os.makedirs(fallback, exist_ok=True)
        return fallback

DOWNLOAD_DIR = _get_download_dir()
