"""Main window: lock screen → shell (sidebar + Assistant / History / Security pages)."""
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from aura.core.assistant import Assistant, Reply
from aura.core.state import AssistantState, AuthMethod
from aura.ui import theme
from aura.ui.lock_screen import LockScreen
from aura.ui.widgets.chat import ChatView
from aura.ui.widgets.visuals import AmbientBackground, CameraView, Orb, PipelineStepper
from aura.ui.workers import CameraWorker, ListenWorker, TaskWorker
from aura.voice import Speaker, SpeechRecognizer


def label(text="", name="", wrap=False) -> QLabel:
    w = QLabel(text)
    if name:
        w.setObjectName(name)
    w.setWordWrap(wrap)
    return w


def card(margins=(20, 18, 20, 18), spacing=10) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("Card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    return frame, layout


SHORT_METHOD = {AuthMethod.FACE: "face recognition", AuthMethod.PIN: "your PIN",
                AuthMethod.PRESENCE: "a presence check", AuthMethod.DEMO: "demo mode"}


def unlocked_via(method: str) -> str:
    return f"Unlocked with {SHORT_METHOD.get(method, method)}"


def greeting() -> str:
    hour = datetime.now().hour
    return "Good morning" if hour < 12 else "Good afternoon" if hour < 18 else "Good evening"


# ── Assistant page (stages 2 + 3) ────────────────────────────────────────────
class AssistantPage(QWidget):
    def __init__(self, window: "MainWindow"):
        super().__init__()
        self.w = window
        self.workers: set = set()
        self.listener: ListenWorker | None = None
        self.busy = False

        col = QVBoxLayout(self)
        col.setContentsMargins(36, 28, 36, 26)
        col.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(16)
        self.orb = Orb(76)
        header.addWidget(self.orb)
        titles = QVBoxLayout()
        titles.setSpacing(2)
        self.title = label(greeting(), "H1")
        self.subtitle = label("Ready when you are.", "Muted")
        titles.addStretch()
        titles.addWidget(self.title)
        titles.addWidget(self.subtitle)
        titles.addStretch()
        header.addLayout(titles, 1)
        self.trust = label("", "PillOk")
        header.addWidget(self.trust, 0, Qt.AlignVCenter)
        self.speak = QCheckBox("Speak replies")
        self.speak.toggled.connect(lambda on: setattr(self.w.speaker, "enabled", on))
        header.addWidget(self.speak, 0, Qt.AlignVCenter)
        col.addLayout(header)

        chat_card, chat_layout = card((10, 10, 6, 10))
        self.chat = ChatView()
        chat_layout.addWidget(self.chat)
        col.addWidget(chat_card, 1)

        chips = QHBoxLayout()
        chips.setSpacing(8)
        for text in window.assistant.suggestions()[:5]:
            chip = QPushButton(text if len(text) < 30 else text[:28] + "…")
            chip.setObjectName("Chip")
            chip.setToolTip(text)
            chip.setCursor(Qt.PointingHandCursor)
            chip.clicked.connect(lambda _=False, t=text: self.submit(t))
            chips.addWidget(chip)
        chips.addStretch()
        col.addLayout(chips)

        composer = QHBoxLayout()
        composer.setSpacing(10)
        self.mic = QPushButton("🎙")
        self.mic.setObjectName("Round")
        self.mic.setCursor(Qt.PointingHandCursor)
        self.mic.clicked.connect(self.toggle_listen)
        self.input = QLineEdit()
        self.input.setObjectName("Composer")
        self.input.setPlaceholderText("Ask AURA…  e.g. “open GitHub” or “create a note called ideas: …”")
        self.input.returnPressed.connect(lambda: self.submit(self.input.text()))
        send = QPushButton("➤")
        send.setObjectName("Send")
        send.setCursor(Qt.PointingHandCursor)
        send.clicked.connect(lambda: self.submit(self.input.text()))
        composer.addWidget(self.mic)
        composer.addWidget(self.input, 1)
        composer.addWidget(send)
        col.addLayout(composer)
        self.hint = label("", "Faint")
        col.addWidget(self.hint)

    def on_unlock(self) -> None:
        s = self.w.s.session
        self.title.setText(greeting())
        since = s.started[11:16] if s.started else ""
        self.subtitle.setText(f"{unlocked_via(s.method)} · since {since}")
        if s.demo:
            self.trust.setObjectName("Pill")
            self.trust.setText("⚠ Identity not verified")
        else:
            self.trust.setObjectName("PillOk")
            self.trust.setText("✓ Verified session")
        self.trust.style().unpolish(self.trust)
        self.trust.style().polish(self.trust)
        voice = self.w.recognizer.available
        self.mic.setEnabled(voice)
        self.mic.setToolTip("Speak a command (offline Vosk)" if voice else "Voice model missing — run scripts/download_models.py --voice")
        self.hint.setText("Enter to send  ·  ⌘L lock  ·  " + ("🎙 click the mic to speak" if voice else "voice input unavailable — type instead"))
        self.chat.clear()
        self.chat.add_reply(f"{greeting()}. You're in — I can open sites, search, launch apps, tell the time "
                            "and keep private notes. Try one of the suggestions below.", "success", "greeting")
        self.set_state(AssistantState.IDLE)
        self.input.setFocus()

    def set_state(self, state: AssistantState, text: str = "") -> None:
        self.orb.set_state(state)
        self.w.sidebar_orb.set_state(state)
        defaults = {AssistantState.IDLE: "Ready when you are.", AssistantState.LISTENING: "Listening…",
                    AssistantState.PROCESSING: "Working on it…"}
        if text or state in defaults:
            s = self.w.s.session
            self.subtitle.setText(text or (defaults[state] if state != AssistantState.IDLE
                                           else unlocked_via(s.method)))

    # Stage 2 — command in
    def submit(self, text: str) -> None:
        text = (text or "").strip()
        if not text or self.busy:
            return
        self.input.clear()
        for c in self.chat.cards:
            c.disable()
        self.chat.add_user(text)
        self._run(self.w.assistant.handle, text)

    def _run(self, fn, *args) -> None:
        self.busy = True
        self.w.stepper.set_states("done", "done", "active")
        self.set_state(AssistantState.PROCESSING)
        worker = TaskWorker(fn, *args, parent=self)
        self.workers.add(worker)
        worker.result.connect(self.on_reply)
        worker.failed.connect(lambda msg: self.on_reply(Reply(msg, "error")))
        worker.finished.connect(lambda: self.workers.discard(worker))
        worker.start()

    # Stage 3 — act / respond
    def on_reply(self, reply: Reply) -> None:
        self.busy = False
        if reply.needs_confirmation:
            card_ = self.chat.add_confirmation(reply.text)
            card_.answered.connect(lambda ok: self._run(self.w.assistant.confirm, ok))
            self.set_state(AssistantState.IDLE, "Waiting for your confirmation…")
            self.w.stepper.set_states("done", "done", "active")
            self.w.speaker.say(reply.text)
            return
        self.chat.add_reply(reply.text, reply.status, reply.intent)
        good = reply.status in ("success", "locked", "exit", "cancelled")
        self.set_state(AssistantState.SUCCESS if good else AssistantState.ERROR)
        self.w.stepper.set_states("done", "done", "done")
        self.w.speaker.say(reply.text)
        if reply.status == "locked":
            QTimer.singleShot(700, self.w.show_lock)
            return
        if reply.status == "exit":
            QTimer.singleShot(700, self.w.close)
            return
        self.w.history.dirty = True
        QTimer.singleShot(1300, self._settle)

    def _settle(self):
        if not self.busy and self.listener is None and self.w.s.session.authenticated:
            self.set_state(AssistantState.IDLE)
            self.w.stepper.set_states("done", "active", "pending")

    # Voice
    def toggle_listen(self) -> None:
        if self.listener is not None:
            self.listener.cancel.set()
            return
        self.listener = ListenWorker(self.w.recognizer, self)
        self.listener.partial.connect(self.input.setText)
        self.listener.heard.connect(self._heard)
        self.listener.failed.connect(self._listen_failed)
        self.mic.setProperty("active", True)
        self.mic.style().unpolish(self.mic)
        self.mic.style().polish(self.mic)
        self.set_state(AssistantState.LISTENING, "Listening… speak now (pause to finish)")
        self.listener.start()

    def _listen_done(self):
        self.listener = None
        self.mic.setProperty("active", False)
        self.mic.style().unpolish(self.mic)
        self.mic.style().polish(self.mic)

    def _heard(self, text: str):
        self._listen_done()
        if text:
            self.submit(text)
        else:
            self.input.clear()
            self.set_state(AssistantState.IDLE, "I didn't catch that — try again or type.")

    def _listen_failed(self, msg: str):
        self._listen_done()
        self.chat.add_reply(msg, "error", "voice")
        self.set_state(AssistantState.ERROR, "Voice unavailable")

    def shutdown(self):
        if self.listener is not None:
            self.listener.stop()
            self._listen_done()
        for w in list(self.workers):
            w.wait(3000)


# ── History page ─────────────────────────────────────────────────────────────
class HistoryPage(QWidget):
    def __init__(self, window: "MainWindow"):
        super().__init__()
        self.w = window
        self.dirty = True
        col = QVBoxLayout(self)
        col.setContentsMargins(36, 30, 36, 30)
        col.setSpacing(16)
        top = QHBoxLayout()
        titles = QVBoxLayout()
        titles.addWidget(label("ACTIVITY", "Eyebrow"))
        titles.addWidget(label("Command history", "H1"))
        titles.addWidget(label("Every command is logged locally. Note contents and private reads are never stored.", "Muted"))
        top.addLayout(titles, 1)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.refresh)
        clear = QPushButton("Clear history")
        clear.setObjectName("Danger")
        clear.clicked.connect(self.clear)
        top.addWidget(refresh, 0, Qt.AlignBottom)
        top.addWidget(clear, 0, Qt.AlignBottom)
        col.addLayout(top)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["When", "Intent", "Status", "Result"])
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setFocusPolicy(Qt.NoFocus)
        header = self.table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        for i, mode in enumerate((QHeaderView.ResizeToContents, QHeaderView.ResizeToContents,
                                  QHeaderView.ResizeToContents, QHeaderView.Stretch)):
            header.setSectionResizeMode(i, mode)
        self.table.verticalHeader().setDefaultSectionSize(40)
        col.addWidget(self.table, 1)
        self.empty = label("No commands yet — head to the Assistant and try one.", "Muted")
        self.empty.setAlignment(Qt.AlignCenter)
        col.addWidget(self.empty)

    def refresh(self):
        rows = self.w.s.repository.history()
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            when = row["started"].replace("T", "  ")[:20]
            items = [when, (row["intent"] or "").replace("_", " "), (row["status"] or "").replace("_", " "),
                     row["message"] or ""]
            for c, value in enumerate(items):
                item = QTableWidgetItem(value)
                if c == 2:
                    item.setForeground(QColor(theme.STATUS_COLOURS.get(row["status"], theme.MUTED)))
                elif c == 0:
                    item.setForeground(QColor(theme.MUTED))
                self.table.setItem(r, c, item)
        self.empty.setVisible(not rows)
        self.dirty = False

    def clear(self):
        if QMessageBox.question(self, "Clear history", "Delete the entire command history?") == QMessageBox.Yes:
            self.w.s.repository.clear_history()
            self.refresh()


# ── Security page ────────────────────────────────────────────────────────────
class SecurityPage(QWidget):
    def __init__(self, window: "MainWindow"):
        super().__init__()
        self.w = window
        self.worker: CameraWorker | None = None
        col = QVBoxLayout(self)
        col.setContentsMargins(36, 30, 36, 30)
        col.setSpacing(18)
        col.addWidget(label("SECURITY & SETUP", "Eyebrow"))
        col.addWidget(label("Face enrollment and system readiness", "H1"))
        row = QHBoxLayout()
        row.setSpacing(18)

        enroll_card, e = card((22, 20, 22, 20), 12)
        e.addWidget(label("Face enrollment", "H2"))
        e.addWidget(label("Captures 5 consistent samples. The template is encrypted with a key held in your OS keychain.", "Muted", True))
        self.camera = CameraView(placeholder="Press Enroll to start")
        self.camera.setFixedHeight(260)
        e.addWidget(self.camera)
        self.status = label("", "Muted", True)
        e.addWidget(self.status)
        buttons = QHBoxLayout()
        self.enroll_btn = QPushButton("Enroll my face")
        self.enroll_btn.setObjectName("Primary")
        self.enroll_btn.clicked.connect(self.toggle_enroll)
        self.delete_btn = QPushButton("Delete enrollment")
        self.delete_btn.setObjectName("Danger")
        self.delete_btn.clicked.connect(self.delete)
        buttons.addWidget(self.enroll_btn, 1)
        buttons.addWidget(self.delete_btn)
        e.addLayout(buttons)
        row.addWidget(enroll_card, 3)

        ready_card, self.ready = card((22, 20, 22, 20), 12)
        row.addWidget(ready_card, 2)
        col.addLayout(row)
        col.addStretch()

    def refresh(self):
        s = self.w.s
        while self.ready.count():
            item = self.ready.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                lay = item.layout()
                while lay.count():
                    w = lay.takeAt(0).widget()
                    if w:
                        w.deleteLater()
        self.ready.addWidget(label("System readiness", "H2"))
        for name, (ok, detail) in s.readiness().items():
            line = QHBoxLayout()
            dot = label("●")
            dot.setStyleSheet(f"color: {theme.OK if ok else theme.WARN}; font-size: 12px;")
            dot.setFixedWidth(16)
            text = QVBoxLayout()
            text.setSpacing(0)
            text.addWidget(label(name))
            text.addWidget(label(detail, "Faint", True))
            line.addWidget(dot, 0, Qt.AlignTop)
            line.addLayout(text, 1)
            self.ready.addLayout(line)
        self.ready.addStretch()
        self.ready.addWidget(label(f"Data · {s.config.data}", "Faint", True))

        if self.worker is None:
            low = s.session.demo
            models = s.config.face_models_ready
            self.enroll_btn.setEnabled(models and not low)
            self.enroll_btn.setText("Re-enroll my face" if s.templates.enrolled else "Enroll my face")
            self.delete_btn.setEnabled(s.templates.enrolled and not low)
            if not models:
                self.status.setText("Face models are missing — run  python scripts/download_models.py --face")
            elif low:
                self.status.setText("Enrollment changes need a verified session. Lock and unlock with your PIN.")
            else:
                self.status.setText("✓ Face enrolled — you can unlock with your face." if s.templates.enrolled
                                    else "Not enrolled yet. Good lighting, one face in view.")

    def toggle_enroll(self):
        if self.worker is not None:
            self.stop()
            self.refresh()
            return
        self.worker = CameraWorker(self.w.s.auth, "enroll", self)
        self.worker.frame.connect(self.camera.set_frame)
        self.worker.status.connect(self.status.setText)
        self.worker.finished_ok.connect(self._done)
        self.worker.failed.connect(self._failed)
        self.camera.set_scanning(True, theme.VIOLET)
        self.enroll_btn.setText("Cancel")
        self.delete_btn.setEnabled(False)
        self.status.setText("Opening camera…")
        self.worker.start()

    def stop(self):
        if self.worker is not None:
            worker, self.worker = self.worker, None
            for signal in (worker.frame, worker.status, worker.finished_ok, worker.failed):
                signal.disconnect()
            worker.stop()
        self.camera.set_scanning(False)

    def _done(self, msg):
        self.worker = None
        self.camera.set_scanning(False)
        self.refresh()
        self.status.setText(f"✓ {msg}. Next time, choose “Unlock with Face”.")

    def _failed(self, msg):
        self.worker = None
        self.camera.set_scanning(False)
        self.refresh()
        self.status.setText(f"✗ {msg}")

    def delete(self):
        if QMessageBox.question(self, "Delete enrollment",
                                "Delete your encrypted face template and its keychain key?") == QMessageBox.Yes:
            self.w.s.templates.delete()
            self.refresh()


# ── Window ───────────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self, services, speak: bool = False):
        super().__init__()
        self.s = services
        self.assistant = Assistant(services)
        self.recognizer = SpeechRecognizer(services.config.vosk_model)
        self.speaker = Speaker(enabled=speak)
        self.setWindowTitle("AURA — Authenticate · Command · Act")
        self.resize(1280, 820)
        self.setMinimumSize(1080, 720)

        root = AmbientBackground()
        root.setObjectName("Root")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        self.setCentralWidget(root)

        self.lock_screen = LockScreen(services, self.assistant)
        self.lock_screen.unlocked.connect(self.on_unlocked)
        self.stack.addWidget(self.lock_screen)
        self.stack.addWidget(self._shell())
        QShortcut(QKeySequence("Ctrl+L"), self, activated=self._lock_shortcut)
        self.show_lock()

    def _shell(self) -> QWidget:
        shell = QWidget()
        row = QHBoxLayout(shell)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(256)
        s = QVBoxLayout(side)
        s.setContentsMargins(20, 24, 20, 20)
        s.setSpacing(8)
        brand = QHBoxLayout()
        brand.setSpacing(10)
        self.sidebar_orb = Orb(38)
        brand.addWidget(self.sidebar_orb)
        name = QVBoxLayout()
        name.setSpacing(0)
        logo = label("AURA")
        logo.setStyleSheet("font-size: 18px; font-weight: 800; letter-spacing: 3px;")
        name.addWidget(logo)
        name.addWidget(label("AI capstone · v1.0", "Faint"))
        brand.addLayout(name, 1)
        s.addLayout(brand)
        s.addSpacing(18)

        s.addWidget(label("PIPELINE", "Eyebrow"))
        s.addSpacing(4)
        self.stepper = PipelineStepper()
        s.addWidget(self.stepper)
        s.addSpacing(18)

        s.addWidget(label("NAVIGATE", "Eyebrow"))
        self.pages = QStackedWidget()
        self.assistant_page = AssistantPage(self)
        self.history = HistoryPage(self)
        self.security = SecurityPage(self)
        group = QButtonGroup(self)
        group.setExclusive(True)
        self.nav = []
        for i, (text, page) in enumerate((("✦   Assistant", self.assistant_page), ("☰   History", self.history),
                                          ("◈   Security && setup", self.security))):
            self.pages.addWidget(page)
            btn = QPushButton(text)
            btn.setObjectName("Nav")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _=False, idx=i: self.go(idx))
            group.addButton(btn)
            s.addWidget(btn)
            self.nav.append(btn)
        s.addStretch()

        session_card = QFrame()
        session_card.setObjectName("Inset")
        sc = QVBoxLayout(session_card)
        sc.setContentsMargins(14, 12, 14, 12)
        sc.setSpacing(3)
        sc.addWidget(label("SESSION", "Eyebrow"))
        self.session_method = label("", wrap=True)
        self.session_method.setStyleSheet("font-weight: 600;")
        self.session_since = label("", "Faint")
        sc.addWidget(self.session_method)
        sc.addWidget(self.session_since)
        s.addWidget(session_card)
        lock = QPushButton("🔒   Lock AURA")
        lock.setCursor(Qt.PointingHandCursor)
        lock.clicked.connect(lambda: (self.assistant.lock(), self.show_lock()))
        s.addWidget(lock)

        row.addWidget(side)
        row.addWidget(self.pages, 1)
        return shell

    def go(self, index: int) -> None:
        self.nav[index].setChecked(True)
        if self.pages.currentWidget() is self.security and index != 2:
            self.security.stop()
        self.pages.setCurrentIndex(index)
        if index == 1:
            self.history.refresh()
        if index == 2:
            self.security.refresh()

    def on_unlocked(self, method: AuthMethod) -> None:
        self.lock_screen.stop_camera()
        session = self.s.session
        self.session_method.setText(session.method)
        self.session_method.setStyleSheet(f"font-weight: 600; color: {theme.WARN if session.demo else theme.OK};")
        self.session_since.setText(f"Started {session.started[11:19]}")
        self.stepper.set_states("done", "active", "pending")
        self.stack.setCurrentIndex(1)
        self.go(0)
        self.assistant_page.on_unlock()

    def show_lock(self) -> None:
        self.assistant_page.shutdown()
        self.security.stop()
        if self.s.session.authenticated:
            self.assistant.lock()
        self.stepper.set_states("active", "pending", "pending")
        self.sidebar_orb.set_state(AssistantState.LOCKED)
        self.lock_screen.refresh()
        self.stack.setCurrentIndex(0)

    def _lock_shortcut(self):
        if self.s.session.authenticated:
            self.show_lock()

    def closeEvent(self, event):
        self.lock_screen.stop_camera()
        self.security.stop()
        self.assistant_page.shutdown()
        self.speaker.stop()
        self.assistant.lock()
        super().closeEvent(event)
