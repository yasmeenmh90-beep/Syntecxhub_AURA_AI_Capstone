import time

import numpy as np


class FaceVerificationService:
    def __init__(self, store, threshold=0.363, required=4, timeout=25.0, clock=time.monotonic):
        self.references = np.asarray(store.load(), dtype=float)
        if self.references.ndim != 2 or not np.isfinite(self.references).all():
            raise ValueError("Invalid enrolled template. Delete enrollment and enroll again.")
        norms = np.linalg.norm(self.references, axis=1, keepdims=True)
        if (norms == 0).any():
            raise ValueError("Invalid enrolled template.")
        self.references /= norms
        self.threshold, self.required, self.timeout = threshold, required, timeout
        self.clock, self.started, self.matches = clock, clock(), 0

    def reset(self) -> None:
        self.matches = 0

    def check(self, embedding) -> bool:
        if self.clock() - self.started >= self.timeout:
            raise TimeoutError("Face verification timed out.")
        vector = np.asarray(embedding, dtype=float).flatten()
        norm = np.linalg.norm(vector)
        if not np.isfinite(vector).all() or norm == 0:
            self.reset()
            return False
        scores = self.references @ (vector / norm)
        # Median avoids one unusually permissive reference dominating the decision.
        self.matches = self.matches + 1 if float(np.median(scores)) >= self.threshold else 0
        return self.matches >= self.required
