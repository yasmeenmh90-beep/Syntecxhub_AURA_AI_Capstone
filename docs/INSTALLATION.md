# Installation

## Requirements
* Python **3.11 or 3.12** (PySide6 6.8 and Vosk do not ship wheels for newer versions yet)
* A webcam (optional: PIN and demo mode work without one)
* A microphone (optional: text input always works)

## 1. Environment
```bash
python3.12 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt  # or requirements.txt for runtime only
pip install -e .                     # optional: adds the `aura-ai` command
```

## 2. Models (optional, explicit)
AURA never downloads anything on its own. Fetch the models once:
```bash
python scripts/download_models.py           # everything
python scripts/download_models.py --face    # YuNet (0.2 MB) + SFace (37 MB) from opencv_zoo
python scripts/download_models.py --voice   # vosk-model-small-en-us-0.15 (~40 MB zip)
```
Models are saved to `./models` (git-ignored). To use another location, set `AURA_MODEL_DIR`.

| File | Purpose | Source |
|---|---|---|
| `face_detection_yunet_2023mar.onnx` | face detection | github.com/opencv/opencv_zoo |
| `face_recognition_sface_2021dec.onnx` | 128-d face embeddings | github.com/opencv/opencv_zoo |
| `vosk-model-small-en-us-0.15/` | offline speech recognition | alphacephei.com/vosk/models |

The **presence check** uses the Haar cascade that ships inside `opencv-python`, so it works with no download.

## 3. Permissions
* **macOS:** the first camera or microphone use triggers a permission prompt for the app that launched Python (Terminal, iTerm or VS Code). If you denied it, re-enable it under System Settings → Privacy & Security.
* **Linux:** `sudo apt install libportaudio2` is needed for the microphone. You also need a keyring backend such as GNOME Keyring or KWallet.
* **Windows:** biometric keys are stored in Windows Credential Manager.

## 4. Verify
```bash
python main.py doctor
pytest -q
```

## Data location
| OS | Default |
|---|---|
| macOS | `~/Library/Application Support/AURA AI` |
| Linux | `~/.local/share/AURA AI` |
| Windows | `%LOCALAPPDATA%\Aura\AURA AI` |

The folder contains `aura.db` (history and preferences), `face-template.enc` and `notes/`. Delete it to reset AURA.
