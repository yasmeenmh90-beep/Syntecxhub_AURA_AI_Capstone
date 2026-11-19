#!/usr/bin/env python3
"""Download the optional offline models into ./models (or $AURA_MODEL_DIR).

    python scripts/download_models.py            # face + voice
    python scripts/download_models.py --face     # YuNet + SFace only (~38 MB)
    python scripts/download_models.py --voice    # Vosk small English (~40 MB)
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aura.core.config import Config  # noqa: E402
from aura.core.models import download_face_models, download_voice_model  # noqa: E402

_last: dict[str, str] = {}


def progress(name: str, done: int, total: int) -> None:
    pct = f"{done * 100 // total:3d}%" if total else f"{done >> 20} MB"
    if _last.get(name) != pct:  # Only redraw when the visible value changes.
        _last[name] = pct
        print(f"\r  ↓ {name:<42} {pct}", end="", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--face", action="store_true", help="download face models only")
    parser.add_argument("--voice", action="store_true", help="download the voice model only")
    parser.add_argument("--force", action="store_true", help="re-download even if present")
    args = parser.parse_args()
    both = not (args.face or args.voice)
    models = Config.load().models
    print(f"Model directory: {models}")
    try:
        if args.face or both:
            saved = download_face_models(models, progress, args.force)
            print(f"\n  ✓ Face models {'downloaded' if saved else 'already present'}")
        if args.voice or both:
            saved = download_voice_model(models, progress, args.force)
            print(f"\n  ✓ Voice model {'downloaded' if saved else 'already present'}")
    except Exception as exc:  # noqa: BLE001 - surface any network/IO error clearly
        print(f"\n  ✗ {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
