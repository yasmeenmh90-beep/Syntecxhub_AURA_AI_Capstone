import numpy as np
import pytest

from aura.authentication.enrollment import FaceEnrollmentService
from aura.authentication.presence import PresenceService
from aura.authentication.verification import FaceVerificationService


class Store:
    def __init__(self, data=None):
        self.data = data

    def save(self, data):
        self.data = data

    def load(self):
        return self.data


def unit(*values):
    v = np.zeros(128)
    v[:len(values)] = values
    return v / np.linalg.norm(v)


def test_enrollment_collects_samples_then_saves():
    store = Store()
    service = FaceEnrollmentService(store, required=3)
    assert not service.add(unit(1)) and not service.add(unit(1, 0.05))
    assert service.add(unit(1, 0.1)) and len(store.data) == 3


def test_enrollment_restarts_if_identity_changes():
    service = FaceEnrollmentService(Store(), required=3)
    service.add(unit(1))
    with pytest.raises(ValueError, match="Identity changed"):
        service.add(unit(0, 1))
    assert service.samples == []


def test_enrollment_rejects_invalid_vectors():
    with pytest.raises(ValueError):
        FaceEnrollmentService(Store()).add(np.zeros(128))


def test_verification_requires_consecutive_matches():
    service = FaceVerificationService(Store([unit(1).tolist()] * 3), required=3)
    assert not service.check(unit(1)) and not service.check(unit(1))
    assert not service.check(unit(0, 1))  # A mismatch resets the streak.
    assert service.matches == 0
    assert [service.check(unit(1)) for _ in range(3)][-1]


def test_verification_times_out():
    t = [0.0]
    service = FaceVerificationService(Store([unit(1).tolist()]), timeout=1.0, clock=lambda: t[0])
    t[0] = 2.0
    with pytest.raises(TimeoutError):
        service.check(unit(1))


def test_verification_rejects_corrupt_template():
    with pytest.raises(ValueError):
        FaceVerificationService(Store([[0.0, 0.0]]))


def test_presence_service():
    service = PresenceService(required=2)
    with pytest.raises(ValueError, match="No face"):
        service.check(0)
    with pytest.raises(ValueError, match="Multiple"):
        service.check(2)
    assert not service.check(1) and service.check(1)
