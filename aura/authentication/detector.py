"""Face detection (YuNet) + recognition embeddings (SFace) using OpenCV's DNN zoo models."""
from pathlib import Path

import numpy as np


class FaceDetector:
    """Detects faces and turns exactly one well-lit face into a unit-length embedding."""

    def __init__(self, models: Path):
        import cv2
        detector = models / "face_detection_yunet_2023mar.onnx"
        recognizer = models / "face_recognition_sface_2021dec.onnx"
        if not detector.is_file() or not recognizer.is_file():
            raise RuntimeError("Face models missing. Run `python scripts/download_models.py` "
                               "or use PIN / presence / demo mode.")
        self.cv = cv2
        self.detector = cv2.FaceDetectorYN.create(str(detector), "", (320, 320), 0.9)
        self.recognizer = cv2.FaceRecognizerSF.create(str(recognizer), "")

    def detect(self, frame) -> np.ndarray:
        """Return an (N, 15) array; columns 0–3 are x, y, w, h."""
        h, w = frame.shape[:2]
        self.detector.setInputSize((w, h))
        _, faces = self.detector.detect(frame)
        return np.empty((0, 15)) if faces is None else faces

    def embedding(self, frame, faces=None) -> np.ndarray:
        faces = self.detect(frame) if faces is None else faces
        h, w = frame.shape[:2]
        if len(faces) == 0:
            raise ValueError("No face detected. Look toward the camera.")
        if len(faces) != 1:
            raise ValueError("Multiple faces detected. Only one person may be in view.")
        face = faces[0]
        x, y, fw, fh = [int(v) for v in face[:4]]
        crop = frame[max(0, y):min(h, y + fh), max(0, x):min(w, x + fw)]
        if min(fw, fh) < 90 or crop.size == 0:
            raise ValueError("Move closer to the camera.")
        gray = self.cv.cvtColor(crop, self.cv.COLOR_BGR2GRAY)
        if not 35 <= float(gray.mean()) <= 225 or self.cv.Laplacian(gray, self.cv.CV_64F).var() < 35:
            raise ValueError("Improve lighting and hold still; face is dark, bright, or blurred.")
        aligned = self.recognizer.alignCrop(frame, face)
        feature = self.recognizer.feature(aligned).flatten().astype(float)
        norm = np.linalg.norm(feature)
        if not np.isfinite(feature).all() or norm == 0:
            raise ValueError("Invalid face embedding.")
        return feature / norm
