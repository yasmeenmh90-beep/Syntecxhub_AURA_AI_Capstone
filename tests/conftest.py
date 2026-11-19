import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from aura.authentication.credentials import MemoryKeyring  # noqa: E402
from aura.commands.platform_adapters import DryRunAdapter  # noqa: E402
from aura.core.config import Config  # noqa: E402
from aura.core.services import Services  # noqa: E402


class FakeCamera:
    """Context-manager camera that yields blank frames."""
    opened = 0

    def __init__(self, index=0):
        self.index = index

    def __enter__(self):
        FakeCamera.opened += 1
        return self

    def read(self):
        return np.zeros((480, 640, 3), dtype=np.uint8)

    def __exit__(self, *_):
        return False


class FakeDetector:
    """Returns one face and a fixed embedding (optionally a sequence of embeddings)."""

    def __init__(self, _models=None, vectors=None, faces=1):
        base = np.zeros(128)
        base[0] = 1.0
        self.vectors = list(vectors) if vectors else [base]
        self.faces, self.i = faces, 0

    def detect(self, _frame):
        return np.tile(np.array([[100, 100, 150, 150] + [0] * 11], dtype=float), (self.faces, 1))

    def embedding(self, _frame, faces=None):
        if len(faces) != 1:
            raise ValueError("Multiple faces detected.")
        v = self.vectors[min(self.i, len(self.vectors) - 1)]
        self.i += 1
        return v


@pytest.fixture
def config(tmp_path):
    cfg = Config(tmp_path / "data", tmp_path / "models", verification_timeout=5.0)
    cfg.prepare()
    return cfg


@pytest.fixture
def adapter():
    return DryRunAdapter(system="Darwin")


@pytest.fixture
def services(config, adapter):
    return Services.build(config, adapter=adapter, keyring_backend=MemoryKeyring(),
                          camera_factory=FakeCamera, detector_factory=FakeDetector,
                          presence_factory=lambda _m: FakeDetector())
