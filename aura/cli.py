"""Rich terminal front-end: authenticate → accept a voice/text command → act."""
from __future__ import annotations

import getpass
import sys
from threading import Event

from rich.align import Align
from rich.box import ROUNDED, SIMPLE_HEAVY
from rich.console import Console, Group
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from aura.authentication.controller import PRESENCE, VERIFY
from aura.core.assistant import Assistant, Reply
from aura.core.state import AuthMethod
from aura.voice import Speaker, SpeechRecognizer, VoiceUnavailable

THEME = Theme({
    "brand": "bold #a78bfa", "accent": "#22d3ee", "muted": "#7c859c", "ok": "bold #34d399",
    "warn": "bold #fbbf24", "err": "bold #f87171", "user": "bold #e2e8f0",
})
STATUS_STYLE = {
    "success": ("ok", "✓"), "error": ("err", "✗"), "rejected": ("warn", "?"),
    "confirmation_required": ("warn", "!"), "cancelled": ("muted", "–"),
    "locked": ("brand", "🔒"), "exit": ("brand", "◆"),
}
LOGO = r"""
   ▄▀█ █ █ █▀█ ▄▀█
   █▀█ █▄█ █▀▄ █▀█"""


class CLI:
    def __init__(self, services, *, console: Console | None = None, voice: bool = False,
                 speak: bool = False):
        self.s = services
        self.assistant = Assistant(services)
        self.console = console or Console(theme=THEME, highlight=False)
        self.recognizer = SpeechRecognizer(services.config.vosk_model)
        self.voice = voice and self.recognizer.available
        self.speaker = Speaker(enabled=speak)

    # ── Presentation ─────────────────────────────────────────────────────
    def banner(self) -> None:
        title = Text(LOGO, style="brand")
        tagline = Text("Offline AI capstone  ·  ", style="muted") + Text(
            "Authenticate → Command → Act", style="accent")
        table = Table(box=SIMPLE_HEAVY, show_header=False, expand=True, padding=(0, 1))
        table.add_column(width=2)
        table.add_column(style="user")
        table.add_column(style="muted")
        for name, (ok, detail) in self.s.readiness().items():
            table.add_row(Text("●", style="ok" if ok else "warn"), name, detail)
        self.console.print(Panel(Group(title, Text(), tagline, Text(), table), box=ROUNDED,
                                 border_style="#3b3f5c", padding=(0, 2)))

    def stage(self, number: int, name: str) -> None:
        self.console.print(Rule(Text(f" {number} · {name} ", style="accent"), style="#2a2f45"))

    def show(self, reply: Reply) -> None:
        style, icon = STATUS_STYLE.get(reply.status, ("muted", "·"))
        body = Text(reply.text, style="user")
        meta = Text(f"{icon} {reply.intent or 'system'} · {reply.status.replace('_', ' ')}", style=style)
        self.console.print(Panel(Group(body, meta), title="[brand]AURA[/]", title_align="left",
                                 border_style=style.split()[-1], box=ROUNDED, padding=(0, 1)))
        self.speaker.say(reply.text)

    # ── Stage 1: authenticate ────────────────────────────────────────────
    def _methods(self) -> list[tuple[str, str]]:
        cfg, store = self.s.config, self.s.templates
        methods = []
        if cfg.face_models_ready and store.enrolled:
            methods.append(("face", "Face recognition (enrolled template)"))
        methods.append(("pin", "PIN / password" + ("" if self.s.credentials.configured else "  — create one now")))
        methods.append(("presence", "Face presence check (detection only, no identity)"))
        methods.append(("demo", "Demo mode (no verification)"))
        return methods

    def authenticate(self, method: str | None = None) -> bool:
        self.stage(1, "Authenticate")
        if method is None:
            options = self._methods()
            for i, (_key, label) in enumerate(options, 1):
                self.console.print(f"  [accent]{i}[/]  {label}")
            choice = Prompt.ask("  Choose", choices=[str(i) for i in range(1, len(options) + 1)],
                                default="1", console=self.console)
            method = options[int(choice) - 1][0]
        try:
            if method == "pin":
                return self._pin()
            if method in ("face", "presence"):
                return self._camera(VERIFY if method == "face" else PRESENCE)
            if method == "demo":
                self.assistant.unlock(AuthMethod.DEMO)
                self.console.print("  [warn]⚠ Demo session — identity was NOT verified.[/]")
                return True
        except KeyboardInterrupt:
            self.console.print("  [muted]Cancelled.[/]")
            return False
        except Exception as exc:  # Show a friendly message instead of a traceback.
            self.console.print(f"  [err]✗ {exc}[/]")
            return False
        self.console.print(f"  [err]Unknown method {method!r}[/]")
        return False

    def _pin(self) -> bool:
        creds = self.s.credentials
        if not creds.configured:
            self.console.print("  [muted]No PIN yet — create one (8+ characters).[/]")
            first = getpass.getpass("  New PIN: ")
            if getpass.getpass("  Repeat PIN: ") != first:
                self.console.print("  [err]✗ PINs did not match.[/]")
                return False
        else:
            first = getpass.getpass("  PIN: ")
        if self.assistant.unlock_with_pin(first):
            self.console.print("  [ok]✓ Unlocked with PIN.[/]")
            return True
        self.console.print("  [err]✗ Incorrect PIN.[/]")
        return False

    def _camera(self, mode: str) -> bool:
        cancel = Event()
        with self.console.status("[accent]Opening camera…", spinner="dots12") as spinner:
            message = self.s.auth.run(mode, cancel, lambda text: spinner.update(f"[accent]{text}"))
        self.assistant.unlock(AuthMethod.FACE if mode == VERIFY else AuthMethod.PRESENCE)
        self.console.print(f"  [ok]✓ {message}.[/]")
        if mode == PRESENCE:
            self.console.print("  [warn]⚠ Presence only — this proves a face is present, not who it is.[/]")
        return True

    # ── Stage 2 + 3: command loop ────────────────────────────────────────
    def _listen(self) -> str:
        with self.console.status("[accent]Listening… speak now", spinner="point") as spinner:
            text = self.recognizer.listen(on_partial=lambda t: spinner.update(f"[accent]“{t}”"))
        self.console.print(f"  [muted]heard:[/] [user]{text or '(nothing)'}[/]")
        return text

    def loop(self) -> int:
        self.stage(2, "Command  ·  " + ("voice + text" if self.voice else "text"))
        hint = "Type a command, [accent]/voice[/] to speak, [accent]/history[/], [accent]/lock[/] or [accent]/quit[/]."
        self.console.print(f"  [muted]Session: {self.s.session.method}.[/] {hint}")
        self.console.print("  [muted]Try:[/] " + "  ·  ".join(f"[accent]{t}[/]" for t in self.assistant.suggestions()[:4]))
        while True:
            try:
                text = Prompt.ask("\n[brand]you ›[/]", console=self.console, default="" if self.voice else ...,
                                  show_default=False)
            except (KeyboardInterrupt, EOFError):
                self.console.print()
                return 0
            text = (text or "").strip()
            if text in ("/quit", "/exit"):
                return 0
            if text == "/history":
                self.history()
                continue
            if text == "/help":
                text = "help"
            if text == "/lock":
                text = "lock"
            if text == "/voice" or (not text and self.voice):
                try:
                    text = self._listen()
                except VoiceUnavailable as exc:
                    self.console.print(f"  [warn]{exc}[/]")
                    continue
                if not text:
                    continue
            if not text:
                continue
            self.stage(3, "Act")
            reply = self.assistant.handle(text)
            self.show(reply)
            if reply.needs_confirmation:
                reply = self.assistant.confirm(Confirm.ask("  Confirm?", default=False, console=self.console))
                self.show(reply)
            if reply.status == "exit":
                return 0
            if reply.status == "locked":
                if not self.authenticate():
                    return 1
                self.stage(2, "Command")

    def history(self) -> None:
        table = Table(box=ROUNDED, border_style="#3b3f5c", header_style="accent", expand=True)
        for column in ("When", "Intent", "Status", "Result"):
            table.add_column(column)
        for row in self.s.repository.history()[:15]:
            style = STATUS_STYLE.get(row["status"], ("muted", ""))[0]
            table.add_row(row["started"][11:19], row["intent"], Text(row["status"], style=style),
                          (row["message"] or "")[:60])
        self.console.print(table if table.row_count else Text("  No history yet.", style="muted"))

    def run(self, method: str | None = None) -> int:
        self.banner()
        for _ in range(3):
            if self.authenticate(method):
                return self.loop()
            method = None
        self.console.print("[err]Authentication failed.[/]")
        return 1


def doctor(services, console: Console | None = None) -> int:
    console = console or Console(theme=THEME)
    CLI(services, console=console).banner()
    cfg = services.config
    console.print(Align.left(Text(f"  data   {cfg.data}\n  models {cfg.models}", style="muted")))
    return 0


def enroll(services, console: Console | None = None) -> int:
    """Enrollment requires an unlocked PIN session, so a stranger cannot replace your face."""
    console = console or Console(theme=THEME)
    cli = CLI(services, console=console)
    if not services.config.face_models_ready:
        console.print("[err]Face models missing.[/] Run [accent]python scripts/download_models.py --face[/].")
        return 1
    console.print(Panel("Unlock with your PIN to enroll a face template.", border_style="#a78bfa", box=ROUNDED))
    if not cli._pin():
        return 1
    with console.status("[accent]Look at the camera…", spinner="dots12") as spinner:
        try:
            msg = services.auth.run("enroll", Event(), lambda t: spinner.update(f"[accent]{t}"))
        except Exception as exc:
            console.print(f"[err]✗ {exc}[/]")
            return 1
    console.print(f"[ok]✓ {msg}.[/] Template encrypted with a key stored in your OS keychain.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(0)
