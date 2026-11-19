"""Dashboard: the assistant at a glance (KPIs, 7-day activity, outcomes, top intents, live feed)."""
from datetime import date, datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from aura.ui import theme
from aura.ui.widgets.charts import BarList, ColumnChart, OutcomeBar, StatTile, legend_row
from aura.ui.widgets.motion import fade_in
from aura.ui.widgets.visuals import Orb

STATUS = {"success": (theme.OK, "Succeeded"), "rejected": (theme.WARN, "Rejected"),
          "cancelled": (theme.MUTED, "Cancelled"), "error": (theme.ERR, "Error"), "locked": (theme.VIOLET, "Locked")}


def _label(text="", name="", wrap=False) -> QLabel:
    w = QLabel(text)
    if name:
        w.setObjectName(name)
    w.setWordWrap(wrap)
    return w


def _card(title: str, subtitle: str = "") -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("Card")
    col = QVBoxLayout(frame)
    col.setContentsMargins(22, 18, 22, 18)
    col.setSpacing(12)
    head = QVBoxLayout()
    head.setSpacing(2)
    head.addWidget(_label(title, "H2"))
    if subtitle:
        head.addWidget(_label(subtitle, "Faint"))
    col.addLayout(head)
    return frame, col


def _ago(stamp: str) -> str:
    try:
        then = datetime.fromisoformat(stamp)
    except ValueError:
        return ""
    seconds = int((datetime.now(then.tzinfo) - then).total_seconds())
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{seconds // 60} min ago"
    if seconds < 86400:
        return f"{seconds // 3600} h ago"
    return then.strftime("%d %b")


class HeroBanner(QFrame):
    """Gradient welcome banner with a large orb and the call to action."""

    def __init__(self, on_start):
        super().__init__()
        self.setMinimumHeight(148)
        row = QHBoxLayout(self)
        row.setContentsMargins(30, 22, 30, 22)
        row.setSpacing(22)
        self.orb = Orb(96)
        row.addWidget(self.orb)
        text = QVBoxLayout()
        text.setSpacing(4)
        text.addStretch()
        self.eyebrow = _label("", "Eyebrow")
        self.title = _label("")
        self.title.setStyleSheet("font-size: 28px; font-weight: 800;")
        self.subtitle = _label("", "Muted", wrap=True)
        text.addWidget(self.eyebrow)
        text.addWidget(self.title)
        text.addWidget(self.subtitle)
        text.addStretch()
        row.addLayout(text, 1)
        start = QPushButton("✦   Ask AURA")
        start.setObjectName("Primary")
        start.setCursor(Qt.PointingHandCursor)
        start.setMinimumWidth(170)
        start.clicked.connect(on_start)
        row.addWidget(start, 0, Qt.AlignVCenter)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(self.rect().adjusted(0, 0, -1, -1), 22, 22)
        g = QLinearGradient(0, 0, self.width(), self.height())
        for stop, colour, alpha in ((0, theme.VIOLET, 0.30), (0.55, "#3B2A7A", 0.20), (1, theme.CYAN, 0.18)):
            c = QColor(colour)
            c.setAlphaF(alpha)
            g.setColorAt(stop, c)
        p.fillPath(path, QColor(theme.SURFACE))
        p.fillPath(path, g)
        p.setPen(QColor(theme.BORDER_HI))
        p.drawPath(path)


class DashboardPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.w = window
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        outer.addWidget(scroll)
        body = QWidget()
        scroll.setWidget(body)
        col = QVBoxLayout(body)
        col.setContentsMargins(36, 28, 36, 30)
        col.setSpacing(18)

        self.hero = HeroBanner(lambda: window.go(window.PAGE_ASSISTANT))
        col.addWidget(self.hero)

        tiles = QGridLayout()
        tiles.setSpacing(16)
        self.t_commands = StatTile("⚡", "Commands run", theme.VIOLET)
        self.t_success = StatTile("✓", "Success rate", theme.CYAN)
        self.t_sessions = StatTile("◉", "Sessions", "#A78BFA")
        self.t_notes = StatTile("✎", "Private notes", "#67E8F9")
        self.tiles = (self.t_commands, self.t_success, self.t_sessions, self.t_notes)
        for i, tile in enumerate(self.tiles):
            tiles.addWidget(tile, 0, i)
        col.addLayout(tiles)

        row = QHBoxLayout()
        row.setSpacing(16)
        activity, a = _card("Activity", "Commands per day · last 7 days · hover a column")
        self.columns = ColumnChart()
        a.addWidget(self.columns, 1)
        row.addWidget(activity, 3)

        right, r = _card("Outcomes", "How every finished command ended")
        self.outcome_value = _label("")
        self.outcome_value.setStyleSheet("font-size: 22px; font-weight: 800;")
        r.addWidget(self.outcome_value)
        self.outcomes = OutcomeBar()
        r.addWidget(self.outcomes)
        self.legend_host = QVBoxLayout()
        r.addLayout(self.legend_host)
        r.addSpacing(6)
        r.addWidget(_label("Top intents", "H2"))
        self.intents = BarList()
        r.addWidget(self.intents)
        r.addStretch()
        row.addWidget(right, 2)
        col.addLayout(row)

        bottom = QHBoxLayout()
        bottom.setSpacing(16)
        feed_card, self.feed = _card("Recent activity", "Latest finished commands")
        bottom.addWidget(feed_card, 3)
        sys_card, self.system = _card("System", "Pipeline components")
        bottom.addWidget(sys_card, 2)
        col.addLayout(bottom)
        col.addStretch()

    # ── data ─────────────────────────────────────────────────────────────
    def refresh(self) -> None:
        s = self.w.s
        stats = s.repository.stats()
        session = s.session
        hour = datetime.now().hour
        greet = "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"
        week = sum(v for _, v in stats["days"])
        self.hero.eyebrow.setText("DASHBOARD  ·  " + date.today().strftime("%A %d %B").upper())
        self.hero.title.setText(f"{greet}. AURA is ready.")
        method = session.method if session.authenticated else "Locked"
        self.hero.subtitle.setText(f"Unlocked with {method}  ·  {week} command{'s' * (week != 1)} this week"
                                   f"  ·  everything runs on this device")

        self.t_commands.set(stats["total"], f"{week} in the last 7 days")
        rate = stats["success_rate"]
        self.t_success.set(None if rate is None else rate * 100, "of decided commands" if rate is not None
                           else "No commands yet", "{:.0f}%")
        self.t_sessions.set(stats["sessions"], f"{stats['face_sessions']} unlocked by face")
        self.t_notes.set(stats["notes"], "Stored locally · contents never logged")

        today = date.today().isoformat()
        self.columns.set_data([("Today" if d == today else date.fromisoformat(d).strftime("%a"),
                                date.fromisoformat(d).strftime("%A %d %B"), v) for d, v in stats["days"]])
        outcomes = stats["outcomes"]
        ok = outcomes.get("success", 0)
        decided = sum(outcomes.get(k, 0) for k in ("success", "rejected", "cancelled", "error"))
        self.outcome_value.setText(f"{ok} of {decided} succeeded" if decided else "Nothing yet")
        self.outcomes.set_data(outcomes)
        while self.legend_host.count():
            old = self.legend_host.takeAt(0).widget()
            if old:
                old.deleteLater()
        self.legend_host.addWidget(legend_row(outcomes))
        self.intents.set_data(stats["intents"][:5])
        self._fill_feed(stats["recent"])
        self._fill_system()
        for i, tile in enumerate(self.tiles):
            fade_in(tile, 260 + i * 80, lift=10)

    @staticmethod
    def _clear(layout, keep: int = 1) -> None:
        """Remove items after `keep`, recursing into nested layouts so no label is left orphaned."""
        def purge(item):
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
            elif item.layout():
                inner = item.layout()
                while inner.count():
                    purge(inner.takeAt(0))
                inner.deleteLater()
        while layout.count() > keep:
            purge(layout.takeAt(keep))

    def _fill_feed(self, rows: list[dict]) -> None:
        self._clear(self.feed)
        if not rows:
            self.feed.addWidget(_label("Nothing yet. Your commands will stream in here.", "Muted"))
            self.feed.addStretch()
            return
        for row in rows:
            colour, word = STATUS.get(row["status"], (theme.MUTED, row["status"]))
            line = QHBoxLayout()
            line.setSpacing(12)
            badge = QLabel(word)
            c = QColor(colour)
            badge.setStyleSheet(f"background: rgba({c.red()},{c.green()},{c.blue()},0.14); color: {colour};"
                                f" border-radius: 9px; padding: 2px 9px; font-size: 11px; font-weight: 700;")
            badge.setFixedWidth(84)
            badge.setAlignment(Qt.AlignCenter)
            text = QVBoxLayout()
            text.setSpacing(0)
            text.addWidget(_label(row["intent"].replace("_", " ").capitalize()))
            message = (row["message"] or "")
            text.addWidget(_label(message[:70] + ("…" if len(message) > 70 else ""), "Faint"))
            line.addWidget(badge, 0, Qt.AlignVCenter)
            line.addLayout(text, 1)
            line.addWidget(_label(_ago(row["started"]), "Faint"), 0, Qt.AlignVCenter)
            self.feed.addLayout(line)
        self.feed.addStretch()

    def _fill_system(self) -> None:
        self._clear(self.system)
        items = self.w.s.readiness()
        ready = sum(ok for ok, _ in items.values())
        head = _label(f"{ready} / {len(items)} ready")
        head.setStyleSheet("font-size: 22px; font-weight: 800;")
        self.system.addWidget(head)
        for name, (ok, detail) in items.items():
            line = QHBoxLayout()
            mark = QLabel("✓" if ok else "!")
            mark.setFixedSize(18, 18)
            mark.setAlignment(Qt.AlignCenter)
            colour = theme.OK if ok else theme.WARN
            mark.setStyleSheet(f"background: {colour}; color: {theme.BG}; border-radius: 9px; font-size: 10px;"
                               f" font-weight: 900;")
            line.addWidget(mark)
            line.addWidget(_label(name), 1)
            state = _label("Ready" if ok else "Needs setup", "Faint")
            state.setToolTip(detail)
            line.addWidget(state)
            self.system.addLayout(line)
        self.system.addStretch()
