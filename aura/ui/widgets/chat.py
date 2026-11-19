"""Chat transcript with styled message bubbles and inline confirmation cards."""
from datetime import datetime

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from aura.ui import theme
from aura.ui.widgets.motion import TypingIndicator, fade_in


class Bubble(QFrame):
    def __init__(self, role: str, text: str, status: str = "", intent: str = ""):
        super().__init__()
        user = role == "user"
        self.setMaximumWidth(560)
        colour = theme.STATUS_COLOURS.get(status, theme.BORDER)
        if user:
            style = f"background: {theme.GRADIENT}; border: none; border-radius: 18px; border-bottom-right-radius: 6px;"
        else:
            style = (f"background: {theme.SURFACE_2}; border: 1px solid {theme.BORDER};"
                     f"border-left: 3px solid {colour}; border-radius: 18px; border-bottom-left-radius: 6px;")
        self.setStyleSheet(f"Bubble {{ {style} }}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 11, 16, 10)
        layout.setSpacing(5)
        body = QLabel(text)
        body.setWordWrap(True)
        body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        body.setStyleSheet(f"font-size: 14px; color: {'white' if user else theme.TEXT}; border: none;")
        layout.addWidget(body)
        meta_text = datetime.now().strftime("%H:%M")
        if not user and intent:
            meta_text = f"{intent.replace('_', ' ')}  ·  {status.replace('_', ' ')}  ·  {meta_text}"
        meta = QLabel(meta_text)
        meta.setStyleSheet(f"font-size: 11px; border: none; color: {'rgba(255,255,255,0.75)' if user else theme.FAINT};")
        meta.setAlignment(Qt.AlignRight if user else Qt.AlignLeft)
        layout.addWidget(meta)


class ConfirmCard(QFrame):
    answered = Signal(bool)

    def __init__(self, question: str):
        super().__init__()
        self.setMaximumWidth(560)
        self.setStyleSheet("ConfirmCard { background: rgba(251,191,36,0.07); border: 1px solid rgba(251,191,36,0.35);"
                           " border-radius: 18px; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        label = QLabel(f"⚠  {question}")
        label.setWordWrap(True)
        label.setStyleSheet(f"color: {theme.WARN}; font-weight: 600; font-size: 14px; border: none;")
        layout.addWidget(label)
        row = QHBoxLayout()
        self.yes = QPushButton("Confirm")
        self.yes.setObjectName("Primary")
        self.no = QPushButton("Cancel")
        for b in (self.yes, self.no):
            b.setCursor(Qt.PointingHandCursor)
        self.yes.clicked.connect(lambda: self._answer(True))
        self.no.clicked.connect(lambda: self._answer(False))
        row.addWidget(self.yes)
        row.addWidget(self.no)
        row.addStretch()
        layout.addLayout(row)

    def _answer(self, value: bool):
        self.disable()
        self.answered.emit(value)

    def disable(self):
        self.yes.setEnabled(False)
        self.no.setEnabled(False)


class ChatView(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        host = QWidget()
        self.column = QVBoxLayout(host)
        self.column.setContentsMargins(8, 8, 14, 8)
        self.column.setSpacing(12)
        self.column.addStretch()
        self.setWidget(host)
        self.cards: list[ConfirmCard] = []

    def _append(self, widget: QWidget, right: bool) -> None:
        row = QHBoxLayout()
        if right:
            row.addStretch()
        row.addWidget(widget)
        if not right:
            row.addStretch()
        self.column.addLayout(row)
        fade_in(widget, 300, lift=10)
        QTimer.singleShot(30, lambda: self.verticalScrollBar().setValue(self.verticalScrollBar().maximum()))

    def add_user(self, text: str) -> None:
        self._append(Bubble("user", text), right=True)

    def add_reply(self, text: str, status: str = "success", intent: str = "") -> None:
        self._append(Bubble("aura", text, status, intent), right=False)

    def add_confirmation(self, question: str) -> ConfirmCard:
        for card in self.cards:
            card.disable()
        card = ConfirmCard(question)
        self.cards.append(card)
        self._append(card, right=False)
        return card

    def show_typing(self) -> None:
        self.hide_typing()
        self.typing = TypingIndicator()
        self._append(self.typing, right=False)

    def hide_typing(self) -> None:
        typing = getattr(self, "typing", None)
        if typing is None:
            return
        self.typing = None
        for i in range(self.column.count()):
            layout = self.column.itemAt(i).layout()
            if layout and layout.indexOf(typing) >= 0:
                self.column.takeAt(i)
                while layout.count():
                    w = layout.takeAt(0).widget()
                    if w:
                        w.deleteLater()
                break

    def clear(self) -> None:
        self.typing = None
        while self.column.count() > 1:
            item = self.column.takeAt(1)
            layout = item.layout()
            if layout:
                while layout.count():
                    w = layout.takeAt(0).widget()
                    if w:
                        w.deleteLater()
        self.cards.clear()
