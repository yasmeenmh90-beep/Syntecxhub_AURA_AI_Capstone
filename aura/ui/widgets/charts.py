"""Dashboard data widgets, custom-painted with QPainter (no chart library needed).

Conventions: magnitude charts use ONE hue (violet); outcome status uses the reserved status colours
and always carries a text label; text uses text tokens, never the series colour; bars have 4 px
rounded data-ends anchored to the baseline; every mark has a hover tooltip; marks grow in once.
"""
from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    Qt,
    QVariantAnimation,
)
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from aura.ui import theme
from aura.ui.widgets.motion import REDUCED

SERIES = theme.VIOLET          # single magnitude hue
SERIES_HOVER = "#A78BFA"


def _bar_path(rect: QRectF, radius: float = 4.0, horizontal: bool = False) -> QPainterPath:
    """Rounded only at the data end (top for columns, right for bars); square at the baseline."""
    path = QPainterPath()
    r = min(radius, rect.width() / 2, rect.height() / 2)
    if r <= 0:
        path.addRect(rect)
        return path
    if horizontal:
        path.moveTo(rect.left(), rect.top())
        path.lineTo(rect.right() - r, rect.top())
        path.quadTo(rect.right(), rect.top(), rect.right(), rect.top() + r)
        path.lineTo(rect.right(), rect.bottom() - r)
        path.quadTo(rect.right(), rect.bottom(), rect.right() - r, rect.bottom())
        path.lineTo(rect.left(), rect.bottom())
    else:
        path.moveTo(rect.left(), rect.bottom())
        path.lineTo(rect.left(), rect.top() + r)
        path.quadTo(rect.left(), rect.top(), rect.left() + r, rect.top())
        path.lineTo(rect.right() - r, rect.top())
        path.quadTo(rect.right(), rect.top(), rect.right(), rect.top() + r)
        path.lineTo(rect.right(), rect.bottom())
    path.closeSubpath()
    return path


class _Animated(QWidget):
    """Base: a 0→1 `progress` property that drives the grow-in."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 1.0
        self.anim = QPropertyAnimation(self, b"progress", self)
        self.anim.setDuration(900)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.setMouseTracking(True)
        self.hover = -1

    def get_progress(self) -> float:
        return self._progress

    def set_progress(self, value: float) -> None:
        self._progress = value
        self.update()

    progress = Property(float, get_progress, set_progress)

    def animate(self) -> None:
        if REDUCED:
            self.set_progress(1.0)
            return
        self.anim.stop()
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()

    def leaveEvent(self, _event):
        self.hover = -1
        QToolTip.hideText()
        self.update()


class CountLabel(QLabel):
    """Hero number that counts up from 0 to its value."""

    def __init__(self, parent=None):
        super().__init__("0", parent)
        self.fmt = "{:,.0f}"
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(1000)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.valueChanged.connect(lambda v: self.setText(self.fmt.format(v)))

    def count_to(self, value: float | None, fmt: str = "{:,.0f}") -> None:
        self.fmt = fmt
        self.anim.stop()
        if value is None:
            self.setText("—")
            return
        if REDUCED:
            self.setText(fmt.format(value))
            return
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(float(value))
        self.anim.start()


class StatTile(QFrame):
    """KPI tile: glyph, label, animated hero number and a muted caption."""

    def __init__(self, glyph: str, title: str, accent: str = theme.VIOLET, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setMinimumHeight(132)
        self.accent = accent
        col = QVBoxLayout(self)
        col.setContentsMargins(20, 18, 20, 16)
        col.setSpacing(4)
        top = QHBoxLayout()
        icon = QLabel(glyph)
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedSize(34, 34)
        tint = QColor(accent)
        icon.setStyleSheet(f"background: rgba({tint.red()},{tint.green()},{tint.blue()},0.16); color: {accent};"
                           f" border-radius: 10px; font-size: 16px; font-weight: 700;")
        name = QLabel(title)
        name.setObjectName("Muted")
        name.setStyleSheet("font-weight: 600;")
        top.addWidget(icon)
        top.addSpacing(6)
        top.addWidget(name, 1)
        col.addLayout(top)
        col.addStretch()
        self.value = CountLabel()
        self.value.setStyleSheet(f"font-size: 34px; font-weight: 800; color: {theme.TEXT};")
        col.addWidget(self.value)
        self.caption = QLabel("")
        self.caption.setObjectName("Faint")
        col.addWidget(self.caption)

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        g = QLinearGradient(0, 0, self.width(), 0)  # accent hairline across the top edge
        c = QColor(self.accent)
        g.setColorAt(0.0, QColor(0, 0, 0, 0))
        g.setColorAt(0.5, c)
        g.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setPen(QPen(g, 2))
        p.drawLine(QPointF(24, 1.5), QPointF(self.width() - 24, 1.5))

    def set(self, value, caption: str = "", fmt: str = "{:,.0f}") -> None:
        self.value.count_to(value, fmt)
        self.caption.setText(caption)


class ColumnChart(_Animated):
    """Single-series vertical columns (e.g. commands per day) with a recessive grid."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(190)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.data: list[tuple[str, str, int]] = []   # (axis label, tooltip label, value)
        self.unit = "commands"

    def set_data(self, data: list[tuple[str, str, int]]) -> None:
        self.data = data
        self.animate()

    def _geometry(self):
        left, right, top, bottom = 34, 8, 14, 26
        plot = QRectF(left, top, self.width() - left - right, self.height() - top - bottom)
        n = max(len(self.data), 1)
        slot = plot.width() / n
        bar_w = min(42.0, slot * 0.56)
        return plot, slot, bar_w

    @staticmethod
    def _nice_max(v: int) -> int:
        for step in (4, 8, 12, 20, 40, 60, 100, 200, 400, 1000):
            if v <= step:
                return step
        return int(v * 1.2)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        plot, slot, bar_w = self._geometry()
        top_value = self._nice_max(max([v for *_, v in self.data] + [1]))
        small = QFont(self.font())
        small.setPixelSize(11)
        p.setFont(small)

        for i in range(5):  # recessive grid + y labels
            y = plot.bottom() - plot.height() * i / 4
            p.setPen(QPen(QColor(theme.BORDER), 1, Qt.SolidLine if i == 0 else Qt.DotLine))
            p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            p.setPen(QColor(theme.FAINT))
            p.drawText(QRectF(0, y - 8, plot.left() - 8, 16), Qt.AlignRight | Qt.AlignVCenter,
                       f"{top_value * i // 4}")

        if not any(v for *_, v in self.data):
            p.setPen(QColor(theme.MUTED))
            p.drawText(plot, Qt.AlignCenter, "No commands yet: try one in the Assistant")

        peak = max(range(len(self.data)), key=lambda k: self.data[k][2]) if self.data else -1
        for i, (axis, _tip, value) in enumerate(self.data):
            cx = plot.left() + slot * (i + 0.5)
            h = plot.height() * value / top_value * self._progress
            if value:
                rect = QRectF(cx - bar_w / 2, plot.bottom() - h, bar_w, h)
                g = QLinearGradient(rect.topLeft(), rect.bottomLeft())
                g.setColorAt(0, QColor(SERIES_HOVER if i == self.hover else SERIES))
                g.setColorAt(1, QColor(theme.VIOLET).darker(150))
                p.fillPath(_bar_path(rect), g)
                if i == peak and self._progress > 0.95:  # selective direct label: the peak only
                    p.setPen(QColor(theme.TEXT))
                    p.drawText(QRectF(cx - 30, rect.top() - 18, 60, 14), Qt.AlignCenter, str(value))
            p.setPen(QColor(theme.TEXT if i == len(self.data) - 1 else theme.MUTED))
            p.drawText(QRectF(cx - slot / 2, plot.bottom() + 6, slot, 16), Qt.AlignCenter, axis)

    def mouseMoveEvent(self, event):
        plot, slot, _ = self._geometry()
        i = int((event.position().x() - plot.left()) // slot) if slot else -1
        i = i if 0 <= i < len(self.data) and plot.contains(QPointF(event.position().x(), plot.center().y())) else -1
        if i != self.hover:
            self.hover = i
            self.update()
        if i >= 0:
            _axis, tip, value = self.data[i]
            QToolTip.showText(event.globalPosition().toPoint(), f"<b>{tip}</b><br>{value} {self.unit}", self)
        else:
            QToolTip.hideText()


class BarList(_Animated):
    """Ranked horizontal bars with the category label above each bar and the value at its end."""

    ROW = 34

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data: list[tuple[str, int]] = []
        self.setMinimumHeight(self.ROW * 3)

    def set_data(self, data: list[tuple[str, int]]) -> None:
        self.data = data
        self.setMinimumHeight(max(self.ROW * len(data), self.ROW * 3))
        self.animate()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        small = QFont(self.font())
        small.setPixelSize(12)
        p.setFont(small)
        if not self.data:
            p.setPen(QColor(theme.MUTED))
            p.drawText(self.rect(), Qt.AlignCenter, "Intents will appear here")
            return
        top = max(v for _, v in self.data)
        width = self.width() - 44
        for i, (name, value) in enumerate(self.data):
            y = i * self.ROW
            p.setPen(QColor(theme.TEXT if i == self.hover else theme.MUTED))
            p.drawText(QRectF(0, y, width, 16), Qt.AlignLeft | Qt.AlignVCenter, name.replace("_", " "))
            track = QRectF(0, y + 19, width, 8)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(theme.SURFACE_3))
            p.drawRoundedRect(track, 4, 4)
            w = max(8.0, width * value / top * self._progress)
            p.fillPath(_bar_path(QRectF(0, y + 19, w, 8), 4, horizontal=True),
                       QColor(SERIES_HOVER if i == self.hover else SERIES))
            p.setPen(QColor(theme.TEXT))
            p.drawText(QRectF(width + 6, y + 13, 38, 20), Qt.AlignLeft | Qt.AlignVCenter, str(value))

    def mouseMoveEvent(self, event):
        i = int(event.position().y() // self.ROW)
        i = i if 0 <= i < len(self.data) else -1
        if i != self.hover:
            self.hover = i
            self.update()
        if i >= 0:
            name, value = self.data[i]
            total = sum(v for _, v in self.data)
            QToolTip.showText(event.globalPosition().toPoint(),
                              f"<b>{name.replace('_', ' ')}</b><br>{value} runs · {value * 100 // max(total, 1)}% of top intents", self)


class OutcomeBar(_Animated):
    """Segmented status bar (success / rejected / cancelled / error) with a labelled legend below."""

    ORDER = (("success", "Succeeded", theme.OK), ("rejected", "Rejected", theme.WARN),
             ("cancelled", "Cancelled", theme.MUTED), ("error", "Errors", theme.ERR))

    def __init__(self, parent=None):
        super().__init__(parent)
        self.counts: dict[str, int] = {}
        self.setFixedHeight(18)

    def set_data(self, counts: dict[str, int]) -> None:
        self.counts = counts
        self.animate()

    def _segments(self):
        total = sum(self.counts.get(k, 0) for k, *_ in self.ORDER)
        if not total:
            return []
        avail = self.width() * self._progress
        x, out = 0.0, []
        for key, name, colour in self.ORDER:
            n = self.counts.get(key, 0)
            if n:
                w = avail * n / total
                out.append((QRectF(x, 0, max(w - 2, 1), self.height()), key, name, colour, n, total))
                x += w
        return out

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(self.rect()), 9, 9)
        p.setClipPath(clip)
        p.fillRect(self.rect(), QColor(theme.SURFACE_3))
        for i, (rect, _key, _name, colour, *_rest) in enumerate(self._segments()):
            c = QColor(colour)
            if i != self.hover and self.hover != -1:
                c.setAlphaF(0.55)
            p.fillRect(rect, c)

    def mouseMoveEvent(self, event):
        x = event.position().x()
        segs = self._segments()
        hit = next((i for i, s in enumerate(segs) if s[0].left() <= x <= s[0].right() + 2), -1)
        if hit != self.hover:
            self.hover = hit
            self.update()
        if hit >= 0:
            _r, _k, name, _c, n, total = segs[hit]
            QToolTip.showText(event.globalPosition().toPoint(), f"<b>{name}</b><br>{n} · {n * 100 // total}%", self)


def legend_row(counts: dict[str, int]) -> QWidget:
    """Legend for OutcomeBar: coloured dot + text label + count, so status is never colour-alone."""
    host = QWidget()
    row = QHBoxLayout(host)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(16)
    for key, name, colour in OutcomeBar.ORDER:
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {colour}; font-size: 11px;")
        text = QLabel(f"{name}  <b>{counts.get(key, 0)}</b>")
        text.setStyleSheet(f"color: {theme.MUTED};")
        pair = QHBoxLayout()
        pair.setSpacing(5)
        pair.addWidget(dot)
        pair.addWidget(text)
        row.addLayout(pair)
    row.addStretch()
    return host
