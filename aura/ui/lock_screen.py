"""Stage 1 — authentication screen (face recognition, PIN, presence check or demo)."""
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from aura.authentication.controller import PRESENCE, VERIFY
from aura.core.state import AuthMethod
from aura.ui import theme
from aura.ui.widgets.visuals import CameraView
from aura.ui.workers import CameraWorker


class GradientTitle(QWidget):
    def __init__(self, text: str, size: int = 64, parent=None):
        super().__init__(parent)
        self.text = text
        self.font_ = QFont()
        self.font_.setPixelSize(size)
        self.font_.setWeight(QFont.Black)
        self.font_.setLetterSpacing(QFont.AbsoluteSpacing, size * 0.12)
        self.setFixedHeight(int(size * 1.25))
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.setFillRule(Qt.WindingFill)
        path.addText(0, self.height() * 0.8, self.font_, self.text)
        g = QLinearGradient(0, 0, path.boundingRect().width(), self.height())
        g.setColorAt(0, QColor("#C4B5FD"))
        g.setColorAt(0.5, QColor(theme.VIOLET))
        g.setColorAt(1, QColor(theme.CYAN))
        p.fillPath(path, g)


def _label(text: str, name: str = "", wrap: bool = True) -> QLabel:
    label = QLabel(text)
    if name:
        label.setObjectName(name)
    label.setWordWrap(wrap)
    return label


class LockScreen(QWidget):
    unlocked = Signal(object)

    def __init__(self, services, assistant, parent=None):
        super().__init__(parent)
        self.s, self.assistant = services, assistant
        self.worker: CameraWorker | None = None
        self.mode = ""

        outer = QHBoxLayout(self)
        outer.setContentsMargins(64, 48, 64, 48)
        outer.setSpacing(56)
        outer.addLayout(self._hero(), 1)
        outer.addWidget(self._card(), 0, Qt.AlignVCenter)

    # ── Layout ───────────────────────────────────────────────────────────
    def _hero(self):
        col = QVBoxLayout()
        col.setSpacing(14)
        col.addStretch()
        col.addWidget(_label("SYNTECXHUB  ·  END-TO-END AI CAPSTONE", "Eyebrow"))
        col.addWidget(GradientTitle("AURA"))
        tagline = _label("An offline assistant that sees you, understands you, and acts for you.", "H1")
        tagline.setStyleSheet("font-size: 22px; font-weight: 600;")
        tagline.setMaximumWidth(520)
        col.addWidget(tagline)
        col.addSpacing(18)
        for number, title, detail in (
            ("01", "Authenticate", "YuNet face detection + SFace recognition, with PIN fallback."),
            ("02", "Command", "Speak with offline Vosk recognition or type — parsed by a rule-based dialog engine."),
            ("03", "Act", "Allow-listed executor with confirmations and a private audit log."),
        ):
            row = QHBoxLayout()
            row.setSpacing(16)
            n = _label(number, wrap=False)
            n.setStyleSheet(f"color: {theme.VIOLET}; font-size: 15px; font-weight: 800;")
            n.setFixedWidth(28)
            n.setAlignment(Qt.AlignTop)
            text = QVBoxLayout()
            text.setSpacing(2)
            text.addWidget(_label(title, "H2"))
            d = _label(detail, "Muted")
            d.setMinimumWidth(380)
            d.setMaximumWidth(460)
            text.addWidget(d)
            row.addWidget(n)
            row.addLayout(text)
            row.addStretch(1)
            col.addLayout(row)
            col.addSpacing(4)
        col.addSpacing(18)
        col.addWidget(_label("●  100% on-device   ·   no cloud calls   ·   encrypted biometrics", "Faint"))
        col.addStretch()
        return col

    def _card(self):
        card = QFrame()
        card.setObjectName("Card")
        card.setFixedWidth(452)
        col = QVBoxLayout(card)
        col.setContentsMargins(26, 26, 26, 24)
        col.setSpacing(12)
        col.addWidget(_label("Unlock AURA", "H1"))
        col.addWidget(_label("Verify it's you to start a session.", "Muted"))
        col.addSpacing(4)

        self.camera = CameraView(placeholder="Camera idle")
        self.camera.setFixedHeight(286)
        col.addWidget(self.camera)
        self.status = _label("", "Muted")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setMinimumHeight(20)
        col.addWidget(self.status)

        self.face_btn = QPushButton("Unlock with Face")
        self.face_btn.setObjectName("Primary")
        self.face_btn.clicked.connect(lambda: self._toggle_camera(VERIFY))
        col.addWidget(self.face_btn)
        row = QHBoxLayout()
        self.presence_btn = QPushButton("Presence check")
        self.presence_btn.setToolTip("Detects that one face is present (OpenCV Haar cascade).\n"
                                     "Does not verify identity — low-assurance session.")
        self.presence_btn.clicked.connect(lambda: self._toggle_camera(PRESENCE))
        self.demo_btn = QPushButton("Demo mode")
        self.demo_btn.setToolTip("Unlock without verification — for presentations only.")
        self.demo_btn.clicked.connect(lambda: self._finish(AuthMethod.DEMO))
        row.addWidget(self.presence_btn)
        row.addWidget(self.demo_btn)
        col.addLayout(row)

        divider = QHBoxLayout()
        for _ in range(2):
            line = QFrame()
            line.setFixedHeight(1)
            line.setStyleSheet(f"background: {theme.BORDER};")
            divider.addWidget(line, 1)
            if _ == 0:
                self.divider_label = _label("or use your PIN", "Faint", wrap=False)
                divider.addWidget(self.divider_label)
        col.addSpacing(2)
        col.addLayout(divider)

        self.pin = QLineEdit()
        self.pin.setEchoMode(QLineEdit.Password)
        self.pin.returnPressed.connect(self._pin_submit)
        self.pin_confirm = QLineEdit()
        self.pin_confirm.setEchoMode(QLineEdit.Password)
        self.pin_confirm.setPlaceholderText("Repeat new PIN")
        self.pin_confirm.returnPressed.connect(self._pin_submit)
        pin_row = QHBoxLayout()
        pin_row.addWidget(self.pin, 1)
        self.pin_btn = QPushButton("Unlock")
        self.pin_btn.clicked.connect(self._pin_submit)
        pin_row.addWidget(self.pin_btn)
        col.addLayout(pin_row)
        col.addWidget(self.pin_confirm)
        self.error = _label("", "Error")
        col.addWidget(self.error)
        return card

    # ── Behaviour ────────────────────────────────────────────────────────
    def refresh(self) -> None:
        """Re-read readiness every time the lock screen is shown."""
        cfg, store = self.s.config, self.s.templates
        face_ready = cfg.face_models_ready and store.enrolled
        self.face_btn.setEnabled(face_ready)
        self.face_btn.setText("Unlock with Face")
        if not cfg.face_models_ready:
            self.face_btn.setToolTip("Face models missing — run scripts/download_models.py")
            self.status.setText("Face unlock not set up · download models, then enroll in Security.")
        elif not store.enrolled:
            self.face_btn.setToolTip("Unlock with your PIN, then enroll your face in Security.")
            self.status.setText("No face enrolled yet · unlock with PIN, then enroll in Security.")
        else:
            self.face_btn.setToolTip("")
            self.status.setText("Ready · look at the camera after pressing Unlock.")
        first_run = not self.s.credentials.configured
        self.pin.setPlaceholderText("Create a PIN (8+ characters)" if first_run else "Enter your PIN")
        self.pin_btn.setText("Create" if first_run else "Unlock")
        self.pin_confirm.setVisible(first_run)
        self.pin.clear()
        self.pin_confirm.clear()
        self.error.clear()
        self.camera.set_scanning(False)
        self._set_busy(False)

    def _set_busy(self, busy: bool, mode: str = "") -> None:
        self.presence_btn.setEnabled(not busy or mode == PRESENCE)
        self.demo_btn.setEnabled(not busy)
        self.pin_btn.setEnabled(not busy)
        if busy:
            self.face_btn.setEnabled(mode == VERIFY)
            target = self.face_btn if mode == VERIFY else self.presence_btn
            target.setText("Cancel")
        else:
            self.presence_btn.setText("Presence check")
            self.face_btn.setText("Unlock with Face")

    def _toggle_camera(self, mode: str) -> None:
        if self.worker is not None:
            self.stop_camera()
            self.refresh()
            return
        self.error.clear()
        self.mode = mode
        self.worker = CameraWorker(self.s.auth, mode, self)
        self.worker.frame.connect(self.camera.set_frame)
        self.worker.status.connect(self.status.setText)
        self.worker.finished_ok.connect(self._camera_ok)
        self.worker.failed.connect(self._camera_failed)
        self.camera.set_scanning(True, theme.CYAN if mode == VERIFY else theme.VIOLET)
        self.status.setText("Opening camera…")
        self._set_busy(True, mode)
        self.worker.start()

    def stop_camera(self) -> None:
        if self.worker is not None:
            worker, self.worker = self.worker, None
            for signal in (worker.frame, worker.status, worker.finished_ok, worker.failed):
                signal.disconnect()
            worker.stop()
        self.camera.set_scanning(False)

    def _camera_ok(self, message: str) -> None:
        self.worker = None
        self.camera.timer.stop()
        self.camera.flash(theme.OK)
        self.status.setText(f"✓ {message}")
        self.status.setStyleSheet(f"color: {theme.OK}; font-weight: 600;")
        method = AuthMethod.FACE if self.mode == VERIFY else AuthMethod.PRESENCE
        QTimer.singleShot(650, lambda: self._finish(method))

    def _camera_failed(self, message: str) -> None:
        self.worker = None
        self.refresh()
        self.camera.flash(theme.ERR)
        self.error.setText(message)

    def _pin_submit(self) -> None:
        secret = self.pin.text()
        if not secret:
            self.error.setText("Enter your PIN.")
            return
        if not self.s.credentials.configured and secret != self.pin_confirm.text():
            self.error.setText("The two PINs do not match.")
            return
        try:
            ok = self.assistant.unlock_with_pin(secret)
        except ValueError as exc:
            self.error.setText(str(exc))
            return
        if not ok:
            self.pin.clear()
            self.error.setText("Incorrect PIN.")
            return
        self.unlocked.emit(AuthMethod.PIN)

    def _finish(self, method: AuthMethod) -> None:
        self.status.setStyleSheet("")
        if method != AuthMethod.PIN:
            self.assistant.unlock(method)
        self.unlocked.emit(method)
