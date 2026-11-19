"""Lightweight face *presence* check using the Haar cascade bundled with OpenCV.

This needs no downloaded models, which makes it ideal for workshops and demos. It proves that
one person is in front of the camera — NOT who they are — so sessions unlocked this way are
flagged as low-assurance everywhere in the UI.
"""
import numpy as np


class PresenceDetector:
    def __init__(self, _models=None):
        import cv2
        path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        self.cv = cv2
        self.cascade = cv2.CascadeClassifier(path)
        if self.cascade.empty():
            raise RuntimeError("OpenCV Haar cascade could not be loaded.")

    def detect(self, frame) -> np.ndarray:
        gray = self.cv.cvtColor(frame, self.cv.COLOR_BGR2GRAY)
        gray = self.cv.equalizeHist(gray)
        faces = self.cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6, minSize=(90, 90))
        return np.asarray(faces, dtype=float).reshape(-1, 4)


class PresenceService:
    """Succeeds after `required` consecutive frames that contain exactly one face."""

    def __init__(self, required: int = 6):
        self.required, self.streak = required, 0

    def reset(self) -> None:
        self.streak = 0

    def check(self, face_count: int) -> bool:
        if face_count == 0:
            self.reset()
            raise ValueError("No face detected. Look toward the camera.")
        if face_count > 1:
            self.reset()
            raise ValueError("Multiple faces detected. Only one person may be in view.")
        self.streak += 1
        return self.streak >= self.required
