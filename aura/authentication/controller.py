"""Camera loop for enrollment, verification and presence checks.

No UI imports: frames and status text are delivered through caller-provided callbacks so the
same controller drives the CLI, the Qt GUI and the tests (which inject fake cameras/detectors).
"""
import time
from collections.abc import Callable
from threading import Event

from aura.authentication.camera import CameraService
from aura.authentication.detector import FaceDetector
from aura.authentication.enrollment import FaceEnrollmentService
from aura.authentication.presence import PresenceDetector, PresenceService
from aura.authentication.verification import FaceVerificationService

ENROLL, VERIFY, PRESENCE = "enroll", "verify", "presence"


def annotate(frame, boxes, ok: bool):
    """Draw face boxes on a copy of the frame (green when the frame counted, amber otherwise)."""
    try:
        import cv2
    except ImportError:  # pragma: no cover - OpenCV is a hard dependency
        return frame
    out = frame.copy()
    colour = (129, 211, 52) if ok else (36, 191, 251)
    for box in boxes:
        x, y, w, h = [int(v) for v in box[:4]]
        cv2.rectangle(out, (x, y), (x + w, y + h), colour, 2, cv2.LINE_AA)
    return out


class AuthenticationController:
    def __init__(self, config, store, camera_factory=CameraService, detector_factory=FaceDetector,
                 presence_factory=PresenceDetector):
        self.config, self.store = config, store
        self.camera_factory, self.detector_factory = camera_factory, detector_factory
        self.presence_factory = presence_factory

    def _service(self, mode: str):
        if mode == ENROLL:
            return FaceEnrollmentService(self.store, threshold=self.config.face_threshold)
        if mode == VERIFY:
            if not self.store.enrolled:
                raise RuntimeError("No face is enrolled yet. Unlock with your PIN and enroll first.")
            return FaceVerificationService(self.store, self.config.face_threshold,
                                           self.config.consistent_matches,
                                           self.config.verification_timeout)
        if mode == PRESENCE:
            return PresenceService(self.config.presence_frames)
        raise ValueError(f"Unknown camera mode: {mode}")

    def run(self, mode: str | bool, cancel: Event, status: Callable[[str], None],
            preview: Callable = lambda _frame: None, camera_index: int | None = None) -> str:
        if isinstance(mode, bool):  # Backwards compatible: run(enroll=True/False, ...)
            mode = ENROLL if mode else VERIFY
        service = self._service(mode)
        detector = (self.presence_factory(self.config.models) if mode == PRESENCE
                    else self.detector_factory(self.config.models))
        index = self.config.camera_index if camera_index is None else camera_index
        deadline = time.monotonic() + self.config.verification_timeout
        with self.camera_factory(index) as camera:
            while not cancel.is_set():
                if time.monotonic() >= deadline:
                    raise TimeoutError("Camera operation timed out. Retry or use your local PIN.")
                frame = camera.read()
                faces = detector.detect(frame)
                counted = False
                try:
                    if mode == PRESENCE:
                        done = service.check(len(faces))
                        status(f"Face present · {service.streak}/{service.required}")
                    else:
                        embedding = detector.embedding(frame, faces)
                        if mode == ENROLL:
                            done = service.add(embedding)
                            status(f"Capturing enrollment samples · {len(service.samples)}/{service.required}")
                        else:
                            done = service.check(embedding)
                            status(f"Checking identity · {service.matches}/{service.required}")
                    counted = True
                    if done:
                        preview(annotate(frame, faces, True))
                        return {ENROLL: "Enrollment complete", VERIFY: "Face verified",
                                PRESENCE: "Face presence confirmed"}[mode]
                except ValueError as error:
                    if mode == VERIFY:
                        service.reset()
                    status(str(error))
                preview(annotate(frame, faces, counted))
                cancel.wait(0.12)
        raise RuntimeError("Camera operation cancelled.")
