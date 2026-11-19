"""Background threads so camera, microphone and commands never freeze the UI."""
from threading import Event

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage


def to_qimage(frame) -> QImage:
    import cv2
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w = rgb.shape[:2]
    return QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy()


class CameraWorker(QThread):
    frame = Signal(QImage)
    status = Signal(str)
    finished_ok = Signal(str)
    failed = Signal(str)

    def __init__(self, controller, mode: str, parent=None):
        super().__init__(parent)
        self.controller, self.mode = controller, mode
        self.cancel = Event()

    def run(self):
        try:
            message = self.controller.run(self.mode, self.cancel, self.status.emit,
                                          lambda f: self.frame.emit(to_qimage(f)))
            self.finished_ok.emit(message)
        except Exception as exc:  # noqa: BLE001 - every failure is shown to the user
            self.failed.emit(str(exc))

    def stop(self):
        self.cancel.set()
        self.wait(3000)


class ListenWorker(QThread):
    partial = Signal(str)
    heard = Signal(str)
    failed = Signal(str)

    def __init__(self, recognizer, parent=None):
        super().__init__(parent)
        self.recognizer = recognizer
        self.cancel = Event()

    def run(self):
        try:
            self.heard.emit(self.recognizer.listen(self.cancel, on_partial=self.partial.emit))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))

    def stop(self):
        self.cancel.set()
        self.wait(3000)


class TaskWorker(QThread):
    """Runs one callable off the UI thread and emits its return value."""
    result = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, *args, parent=None):
        super().__init__(parent)
        self.fn, self.args = fn, args

    def run(self):
        try:
            self.result.emit(self.fn(*self.args))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
