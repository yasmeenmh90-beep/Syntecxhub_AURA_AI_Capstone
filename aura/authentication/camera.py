class CameraService:
    def __init__(self, index: int = 0):
        self.index = index
        self.capture = None

    def __enter__(self):
        import cv2
        self.capture = cv2.VideoCapture(self.index)
        if not self.capture.isOpened():
            self.capture.release()
            raise RuntimeError("Camera unavailable. Check OS permission, connection, and camera index.")
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        return self

    def read(self):
        ok, frame = self.capture.read()
        if not ok:
            raise RuntimeError("Camera disconnected or frame capture failed.")
        return frame

    def __exit__(self, *_):
        if self.capture is not None:
            self.capture.release()
