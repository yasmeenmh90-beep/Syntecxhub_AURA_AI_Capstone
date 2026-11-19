"""Explicit, opt-in model downloads (AURA never downloads anything implicitly)."""
import shutil
import tempfile
import urllib.request
import zipfile
from collections.abc import Callable
from pathlib import Path

from aura.core.config import VOSK_MODEL_NAME

FACE_MODELS = {
    "face_detection_yunet_2023mar.onnx":
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "face_recognition_sface_2021dec.onnx":
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
}
VOSK_URL = f"https://alphacephei.com/vosk/models/{VOSK_MODEL_NAME}.zip"
MIN_BYTES = 100_000  # Guards against saving a Git-LFS pointer or an HTML error page.


def _fetch(url: str, target: Path, progress: Callable[[str, int, int], None]) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "aura-model-fetch/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False, suffix=".part") as tmp:
            while chunk := response.read(1 << 16):
                tmp.write(chunk)
                done += len(chunk)
                progress(target.name, done, total)
    part = Path(tmp.name)
    if done < MIN_BYTES:
        part.unlink(missing_ok=True)
        raise RuntimeError(f"{target.name}: download too small ({done} bytes) — check the URL/network.")
    part.replace(target)


def download_face_models(models: Path, progress=lambda *_: None, force=False) -> list[Path]:
    models.mkdir(parents=True, exist_ok=True)
    saved = []
    for name, url in FACE_MODELS.items():
        target = models / name
        if target.is_file() and target.stat().st_size >= MIN_BYTES and not force:
            continue
        _fetch(url, target, progress)
        saved.append(target)
    return saved


def download_voice_model(models: Path, progress=lambda *_: None, force=False) -> Path | None:
    models.mkdir(parents=True, exist_ok=True)
    destination = models / VOSK_MODEL_NAME
    if destination.is_dir() and not force:
        return None
    archive = models / f"{VOSK_MODEL_NAME}.zip"
    _fetch(VOSK_URL, archive, progress)
    with tempfile.TemporaryDirectory(dir=models) as staging:
        with zipfile.ZipFile(archive) as zf:
            root = Path(staging).resolve()
            for member in zf.namelist():  # Zip-slip guard
                if not (root / member).resolve().is_relative_to(root):
                    raise RuntimeError(f"Unsafe path in archive: {member}")
            zf.extractall(root)
        if destination.exists():
            shutil.rmtree(destination)
        (Path(staging) / VOSK_MODEL_NAME).replace(destination)
    archive.unlink(missing_ok=True)
    return destination
