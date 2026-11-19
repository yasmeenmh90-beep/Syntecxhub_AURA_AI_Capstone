"""Motion helpers: page transitions, fade-ins, toasts and a typing indicator.

Every effect is short (≤ 350 ms) and removes its QGraphicsEffect when done, so idle widgets
paint at full speed. Set AURA_REDUCED_MOTION=1 to turn transitions off.
"""
import math
import os

from PySide6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QParallelAnimationGroup,
    QPoint,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
)
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QWidget,
)

from aura.ui import theme

REDUCED = os.environ.get("AURA_REDUCED_MOTION") == "1"


def fade_in(widget: QWidget, duration: int = 280, lift: int = 0) -> None:
    """Fade a widget in (optionally sliding it up by `lift` px)."""
    if REDUCED:
        return
    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(0.0)
    widget.setGraphicsEffect(effect)
    group = QParallelAnimationGroup(widget)
    fade = QPropertyAnimation(effect, b"opacity", widget)
    fade.setDuration(duration)
    fade.setStartValue(0.0)
    fade.setEndValue(1.0)
    fade.setEasingCurve(QEasingCurve.OutCubic)
    group.addAnimation(fade)
    if lift:
        def start_slide():
            end = widget.pos()
            slide = QPropertyAnimation(widget, b"pos", widget)
            slide.setDuration(duration)
            slide.setStartValue(end + QPoint(0, lift))
            slide.setEndValue(end)
            slide.setEasingCurve(QEasingCurve.OutCubic)
            slide.start(QAbstractAnimation.DeleteWhenStopped)
        QTimer.singleShot(0, start_slide)  # after layout has positioned the widget

    def done():
        if widget.graphicsEffect() is effect:
            widget.setGraphicsEffect(None)
    group.finished.connect(done)
    group.start(QAbstractAnimation.DeleteWhenStopped)


class AnimatedStack(QStackedWidget):
    """QStackedWidget that cross-fades and slides the incoming page."""

    def setCurrentIndex(self, index: int) -> None:  # noqa: N802 - Qt naming
        if index == self.currentIndex():
            return
        super().setCurrentIndex(index)
        fade_in(self.currentWidget(), 300, lift=14)

    def setCurrentWidget(self, widget) -> None:  # noqa: N802
        self.setCurrentIndex(self.indexOf(widget))


class Toast(QFrame):
    """Pill notification that slides in at the top-right of its parent and fades away."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        row = QHBoxLayout(self)
        row.setContentsMargins(14, 10, 18, 10)
        row.setSpacing(10)
        self.icon = QLabel()
        self.text = QLabel()
        self.text.setStyleSheet(f"color: {theme.TEXT}; font-weight: 600; background: transparent;")
        row.addWidget(self.icon)
        row.addWidget(self.text)
        self.hide()
        self.timer = QTimer(self, singleShot=True, timeout=self._dismiss)

    def show_message(self, text: str, kind: str = "success", ms: int = 2600) -> None:
        colour = {"success": theme.OK, "error": theme.ERR, "warning": theme.WARN}.get(kind, theme.CYAN)
        glyph = {"success": "✓", "error": "✕", "warning": "!"}.get(kind, "i")
        self.icon.setText(glyph)
        self.icon.setStyleSheet(f"background: {colour}; color: {theme.BG}; border-radius: 10px; font-weight: 800;"
                                f" min-width: 20px; max-width: 20px; min-height: 20px; max-height: 20px;"
                                f" qproperty-alignment: AlignCenter;")
        self.setStyleSheet(f"#Toast {{ background: {theme.SURFACE_3}; border: 1px solid {theme.BORDER_HI};"
                           f" border-left: 3px solid {colour}; border-radius: 14px; }}")
        self.text.setText(text)
        self.adjustSize()
        parent = self.parentWidget()
        self.move(parent.width() - self.width() - 24, 20)
        self.show()
        self.raise_()
        fade_in(self, 260, lift=-12)
        self.timer.start(ms)

    def _dismiss(self):
        if REDUCED:
            self.hide()
            return
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(300)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.finished.connect(lambda: (self.hide(), self.setGraphicsEffect(None)))
        anim.start(QAbstractAnimation.DeleteWhenStopped)


class TypingIndicator(QWidget):
    """Three bouncing dots in an assistant-style bubble, shown while AURA is working."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(76, 40)
        self.phase = 0.0
        self.timer = QTimer(self, interval=16, timeout=self._tick)
        self.timer.start()

    def _tick(self):
        self.phase += 0.016
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QColor(theme.BORDER))
        p.setBrush(QColor(theme.SURFACE_2))
        p.drawRoundedRect(QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), 18, 18)
        p.setPen(Qt.NoPen)
        for i in range(3):
            t = self.phase * 6 - i * 0.7
            bounce = max(0.0, math.sin(t)) * 5
            c = QColor(theme.VIOLET if i != 1 else theme.CYAN)
            c.setAlphaF(0.55 + 0.45 * max(0.0, math.sin(t)))
            p.setBrush(c)
            p.drawEllipse(QRectF(20 + i * 14, self.height() / 2 - 3.5 - bounce, 7, 7))

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)
