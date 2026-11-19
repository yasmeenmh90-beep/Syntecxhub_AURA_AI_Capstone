"""Custom-painted widgets: ambient background, state orb, camera viewport and pipeline stepper."""
import math

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from aura.core.state import AssistantState
from aura.ui import theme


def _alpha(colour: str, a: float) -> QColor:
    c = QColor(colour)
    c.setAlphaF(max(0.0, min(1.0, a)))
    return c


class AmbientBackground(QWidget):
    """Root surface with two soft colour glows — gives the app depth without images."""

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(theme.BG))
        w, h = self.width(), self.height()
        for centre, radius, colour, a in ((QPointF(w * 0.15, -h * 0.05), w * 0.55, theme.VIOLET, 0.20),
                                          (QPointF(w * 1.0, h * 1.05), w * 0.5, theme.CYAN, 0.13)):
            g = QRadialGradient(centre, radius)
            g.setColorAt(0, _alpha(colour, a))
            g.setColorAt(1, _alpha(colour, 0))
            p.fillRect(self.rect(), g)


class Orb(QWidget):
    """Animated sphere whose colour and motion reflect the assistant state."""

    PALETTE = {
        AssistantState.IDLE: (theme.VIOLET, theme.CYAN),
        AssistantState.LISTENING: (theme.CYAN, "#3B82F6"),
        AssistantState.PROCESSING: ("#F59E0B", theme.VIOLET),
        AssistantState.SPEAKING: (theme.OK, theme.CYAN),
        AssistantState.SUCCESS: (theme.OK, theme.CYAN),
        AssistantState.ERROR: (theme.ERR, "#F59E0B"),
        AssistantState.LOCKED: ("#475077", "#2A3155"),
    }

    def __init__(self, size: int = 72, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.state = AssistantState.IDLE
        self.phase = 0.0
        self.timer = QTimer(self, interval=16, timeout=self._tick)
        self.timer.start()

    def set_state(self, state: AssistantState) -> None:
        self.state = state
        self.update()

    def _tick(self):
        self.phase += 0.016
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        a, b = self.PALETTE.get(self.state, self.PALETTE[AssistantState.IDLE])
        speed = {AssistantState.LISTENING: 6, AssistantState.PROCESSING: 4,
                 AssistantState.SPEAKING: 8}.get(self.state, 1.6)
        pulse = 0.5 + 0.5 * math.sin(self.phase * speed)
        r = min(self.width(), self.height()) / 2
        c = QPointF(self.width() / 2, self.height() / 2)
        p.setPen(Qt.NoPen)

        glow = QRadialGradient(c, r)
        glow.setColorAt(0.35, _alpha(a, 0.30 + 0.25 * pulse))
        glow.setColorAt(1.0, _alpha(a, 0))
        p.setBrush(glow)
        p.drawEllipse(c, r, r)

        if self.state == AssistantState.LISTENING:  # Expanding sonar rings
            for k in range(2):
                t = (self.phase * 0.9 + k * 0.5) % 1.0
                p.setPen(QPen(_alpha(b, 0.6 * (1 - t)), 1.6))
                p.setBrush(Qt.NoBrush)
                rr = r * (0.55 + 0.42 * t)
                p.drawEllipse(c, rr, rr)
            p.setPen(Qt.NoPen)

        core = r * 0.5 * (1 + 0.06 * pulse)
        sphere = QRadialGradient(c - QPointF(core * 0.35, core * 0.45), core * 1.7)
        sphere.setColorAt(0.0, QColor("#FFFFFF"))
        sphere.setColorAt(0.22, QColor(b))
        sphere.setColorAt(1.0, QColor(a).darker(170))
        p.setBrush(sphere)
        p.drawEllipse(c, core, core)

        if self.state in (AssistantState.PROCESSING, AssistantState.IDLE):
            pen = QPen(_alpha(b, 0.9 if self.state == AssistantState.PROCESSING else 0.35), 2.2)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            ring = core * 1.38
            rect = QRectF(c.x() - ring, c.y() - ring, ring * 2, ring * 2)
            start = int(-self.phase * (260 if self.state == AssistantState.PROCESSING else 40) * 16) % 5760
            p.drawArc(rect, start, 110 * 16)


class CameraView(QWidget):
    """Rounded, mirrored camera viewport with scan-line and corner-bracket overlay."""

    def __init__(self, parent=None, placeholder: str = "Camera off"):
        super().__init__(parent)
        self.setMinimumSize(320, 240)
        self.image: QImage | None = None
        self.placeholder = placeholder
        self.scanning = False
        self.accent = QColor(theme.CYAN)
        self.phase = 0.0
        self.timer = QTimer(self, interval=16, timeout=self._tick)

    def set_frame(self, image: QImage) -> None:
        self.image = image
        self.update()

    def set_scanning(self, on: bool, colour: str = theme.CYAN) -> None:
        self.scanning, self.accent = on, QColor(colour)
        (self.timer.start() if on else self.timer.stop())
        if not on:
            self.image = None
        self.update()

    def flash(self, colour: str) -> None:
        self.accent = QColor(colour)
        self.update()

    def _tick(self):
        self.phase = (self.phase + 0.012) % 1.0
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        path = QPainterPath()
        path.addRoundedRect(rect, 22, 22)
        p.setClipPath(path)
        bg = QLinearGradient(rect.topLeft(), rect.bottomRight())
        bg.setColorAt(0, QColor("#0E1328"))
        bg.setColorAt(1, QColor("#0A0E1D"))
        p.fillRect(rect, bg)

        if self.image is not None and not self.image.isNull():
            img = self.image.mirrored(True, False).scaled(
                self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            p.drawImage(QPointF((self.width() - img.width()) / 2, (self.height() - img.height()) / 2), img)
            shade = QLinearGradient(rect.topLeft(), rect.bottomLeft())
            shade.setColorAt(0.6, _alpha("#000000", 0))
            shade.setColorAt(1.0, _alpha("#000000", 0.45))
            p.fillRect(rect, shade)
        else:
            c = rect.center()
            pen = QPen(_alpha(theme.MUTED, 0.45), 1.6, Qt.DashLine)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(c + QPointF(0, -14), rect.width() * 0.16, rect.height() * 0.28)
            p.setPen(QColor(theme.FAINT))
            p.drawText(QRectF(rect.left(), c.y() + rect.height() * 0.3, rect.width(), 24),
                       Qt.AlignCenter, self.placeholder)

        if self.scanning:
            y = rect.top() + rect.height() * self.phase
            g = QLinearGradient(0, y - 40, 0, y)
            g.setColorAt(0, _alpha(self.accent.name(), 0))
            g.setColorAt(1, _alpha(self.accent.name(), 0.28))
            p.fillRect(QRectF(rect.left(), y - 40, rect.width(), 40), g)
            p.setPen(QPen(_alpha(self.accent.name(), 0.9), 1.4))
            p.drawLine(QPointF(rect.left() + 12, y), QPointF(rect.right() - 12, y))

        p.setClipping(False)
        p.setPen(QPen(QColor(theme.BORDER), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(rect, 22, 22)
        pen = QPen(self.accent if self.scanning else QColor(theme.BORDER_HI), 3)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        m, L = 18, 26
        for x, y, dx, dy in ((rect.left() + m, rect.top() + m, 1, 1), (rect.right() - m, rect.top() + m, -1, 1),
                             (rect.left() + m, rect.bottom() - m, 1, -1), (rect.right() - m, rect.bottom() - m, -1, -1)):
            p.drawLine(QPointF(x, y), QPointF(x + dx * L, y))
            p.drawLine(QPointF(x, y), QPointF(x, y + dy * L))


class _StepDot(QWidget):
    def __init__(self, number: int):
        super().__init__()
        self.number, self.state = number, "pending"
        self.setFixedSize(30, 30)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(2, 2, 26, 26)
        if self.state == "done":
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(theme.OK))
            p.drawEllipse(r)
            pen = QPen(QColor(theme.BG), 2.4)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.drawPolyline([QPointF(9.5, 15.5), QPointF(13.5, 19.5), QPointF(20.5, 11.5)])
            return
        if self.state == "active":
            g = QLinearGradient(r.topLeft(), r.bottomRight())
            g.setColorAt(0, QColor(theme.VIOLET))
            g.setColorAt(1, QColor(theme.CYAN))
            p.setPen(Qt.NoPen)
            p.setBrush(g)
        else:
            p.setPen(QPen(QColor(theme.BORDER_HI), 1.4))
            p.setBrush(QColor(theme.SURFACE))
        p.drawEllipse(r)
        p.setPen(QColor("white" if self.state == "active" else theme.MUTED))
        f = p.font()
        f.setBold(True)
        p.setFont(f)
        p.drawText(r, Qt.AlignCenter, str(self.number))


class PipelineStepper(QWidget):
    """Vertical Authenticate → Command → Act indicator for the sidebar."""

    STEPS = (("Authenticate", "Face · PIN · presence"), ("Command", "Voice or text"), ("Act", "Allow-listed executor"))

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.dots, self.titles = [], []
        for i, (title, sub) in enumerate(self.STEPS, 1):
            row = QHBoxLayout()
            row.setSpacing(12)
            dot = _StepDot(i)
            text = QVBoxLayout()
            text.setSpacing(0)
            t = QLabel(title)
            t.setObjectName("H2")
            t.setStyleSheet("font-size: 13px;")
            s = QLabel(sub)
            s.setObjectName("Faint")
            text.addWidget(t)
            text.addWidget(s)
            row.addWidget(dot)
            row.addLayout(text, 1)
            layout.addLayout(row)
            self.dots.append(dot)
            self.titles.append(t)

    def set_states(self, *states: str) -> None:
        for dot, title, state in zip(self.dots, self.titles, states, strict=False):
            dot.state = state
            dot.update()
            colour = theme.TEXT if state != "pending" else theme.MUTED
            title.setStyleSheet(f"font-size: 13px; color: {colour};")
