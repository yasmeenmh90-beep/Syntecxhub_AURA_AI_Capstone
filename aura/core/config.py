"""User-specific paths; models are never downloaded implicitly."""
import os
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_data_path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VOSK_MODEL_NAME = "vosk-model-small-en-us-0.15"


def _default_models() -> Path:
    bundled = PROJECT_ROOT / "models"
    return bundled if bundled.is_dir() else Path.cwd() / "models"


@dataclass(frozen=True)
class Config:
    data: Path
    models: Path
    face_threshold: float = 0.363  # OpenCV SFace LFW cosine operating point.
    verification_timeout: float = 25.0
    consistent_matches: int = 4
    presence_frames: int = 6
    camera_index: int = 0

    @classmethod
    def load(cls, data: Path | None = None) -> "Config":
        data = Path(data or os.environ.get("AURA_DATA_DIR") or user_data_path("AURA AI", "Aura"))
        models = Path(os.environ.get("AURA_MODEL_DIR") or _default_models())
        camera = int(os.environ.get("AURA_CAMERA_INDEX", "0") or 0)
        return cls(data.expanduser().resolve(), models.expanduser().resolve(), camera_index=camera)

    def prepare(self) -> None:
        self.data.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.data.chmod(0o700)
        self.notes.mkdir(exist_ok=True, mode=0o700)

    @property
    def notes(self) -> Path:
        return self.data / "notes"

    @property
    def database(self) -> Path:
        return self.data / "aura.db"

    @property
    def face_detector_model(self) -> Path:
        return self.models / "face_detection_yunet_2023mar.onnx"

    @property
    def face_recognizer_model(self) -> Path:
        return self.models / "face_recognition_sface_2021dec.onnx"

    @property
    def face_models_ready(self) -> bool:
        return self.face_detector_model.is_file() and self.face_recognizer_model.is_file()

    @property
    def vosk_model(self) -> Path:
        override = os.environ.get("AURA_VOSK_MODEL")
        return Path(override).expanduser().resolve() if override else self.models / VOSK_MODEL_NAME

    @property
    def voice_model_ready(self) -> bool:
        return (self.vosk_model / "am").is_dir() or (self.vosk_model / "conf").is_dir()
