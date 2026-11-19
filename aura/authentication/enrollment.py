import numpy as np


class FaceEnrollmentService:
    def __init__(self, store, required: int = 5, threshold: float = 0.363):
        self.store = store
        self.required = required
        self.threshold = threshold
        self.samples = []

    def add(self, embedding) -> bool:
        sample = np.asarray(embedding, dtype=float).flatten()
        norm = np.linalg.norm(sample)
        if not np.isfinite(sample).all() or norm == 0:
            raise ValueError("Invalid enrollment embedding.")
        sample /= norm
        if self.samples and float(np.dot(sample, self.samples[0])) < self.threshold:
            self.samples.clear()
            raise ValueError("Identity changed during enrollment. Restarting samples.")
        self.samples.append(sample)
        if len(self.samples) >= self.required:
            self.store.save([s.tolist() for s in self.samples])
            return True
        return False
