"""The capstone pipeline: authenticate → accept a voice/text command → act.

`Assistant` is UI-agnostic. The CLI, the Qt GUI and the scripted demo all drive it the same way,
so each stage (vision, dialog, executor) stays an independent, reusable module.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime

from aura.commands.executor import ExecutionResult
from aura.commands.validator import DISPLAY_NAMES
from aura.core.state import AuthMethod
from aura.dialog.intents import Intent

YES = {"yes", "y", "yeah", "yep", "sure", "confirm", "ok", "okay", "do it", "go ahead"}
NO = {"no", "n", "nope", "cancel", "stop", "don't", "dont", "abort"}


@dataclass(frozen=True)
class Reply:
    text: str
    status: str            # success | error | rejected | confirmation_required | cancelled | locked | exit
    intent: str = ""
    parameters: dict | None = None

    @property
    def needs_confirmation(self) -> bool:
        return self.status == "confirmation_required"


def describe(intent: Intent) -> str:
    """One-line description used when asking the user to confirm an action."""
    p = intent.parameters
    return {
        "open_website": f"Open {DISPLAY_NAMES.get(p.get('website', '').lower(), p.get('website', ''))} in your default browser?",
        "search_web": f"Search the web for “{p.get('query', '')}”?",
        "open_application": f"Launch the {p.get('application', '')}?",
        "create_note": f"Overwrite the existing note “{p.get('title', '')}”?",
        "read_note": f"Show the private note “{p.get('title', '')}”?",
        "list_notes": "Show the names of your private notes?",
        "exit_application": "Exit AURA?",
    }.get(intent.name, "Run this command?")


class Assistant:
    def __init__(self, services):
        self.s = services
        self.pending: Intent | None = None

    # ── Stage 1: authentication ──────────────────────────────────────────
    @property
    def unlocked(self) -> bool:
        return self.s.session.authenticated

    def unlock(self, method: AuthMethod) -> None:
        self.s.session.unlock(method)
        self.s.repository.record_session(self.s.session.started, str(method))

    def unlock_with_pin(self, secret: str) -> bool:
        creds = self.s.credentials
        if not creds.configured:
            creds.setup(secret)
        elif not creds.verify(secret):
            return False
        self.unlock(AuthMethod.PIN)
        return True

    def lock(self) -> None:
        self.pending = None
        self.s.session.lock()

    # ── Stage 2 + 3: understand and act ──────────────────────────────────
    def handle(self, text: str) -> Reply:
        if not self.unlocked:
            return Reply("AURA is locked. Authenticate first.", "locked")
        text = (text or "").strip()
        if self.pending is not None:
            answer = text.lower().rstrip(".!")
            if answer in YES:
                return self.confirm(True)
            if answer in NO:
                return self.confirm(False)
            self.pending = None  # Any other input abandons the pending confirmation.
        shortcut = self.s.repository.shortcuts().get(text.lower())
        intent = self.s.dialog.match(shortcut or text)
        if intent.name == "unknown_command" and self.s.smalltalk is not None:
            answer = self.s.smalltalk.respond(text)
            if answer is not None:
                return self._chat(answer)
        return self._run(intent, confirmed=False)

    def _chat(self, answer) -> Reply:
        """Week 2 small-talk / knowledge reply. It performs no action, so no confirmation."""
        name = "knowledge" if answer.tag == "knowledge" else f"chat_{answer.tag}"
        stamp = datetime.now().astimezone().isoformat(timespec="milliseconds")
        message = f"Answered: {answer.topic}" if answer.topic else answer.text
        self.s.repository.record(ExecutionResult(str(uuid.uuid4()), name, "success", message, stamp, stamp))
        return Reply(answer.text, "success", name)

    def confirm(self, accept: bool) -> Reply:
        intent, self.pending = self.pending, None
        if intent is None:
            return Reply("There is nothing waiting for confirmation.", "rejected")
        if not accept:
            return Reply("Cancelled. Nothing was changed.", "cancelled", intent.name, intent.parameters)
        return self._run(intent, confirmed=True)

    def _run(self, intent: Intent, confirmed: bool) -> Reply:
        result = self.s.executor.execute(intent, confirmed=confirmed)
        if result.status == "confirmation_required":
            self.pending = intent
            return Reply(describe(intent), result.status, intent.name, intent.parameters)
        if result.status == "success" and intent.name == "lock_assistant":
            self.lock()
            return Reply(result.message, "locked", intent.name)
        if result.status == "success" and intent.name == "exit_application":
            return Reply(result.message, "exit", intent.name)
        return Reply(result.message, result.status, intent.name, intent.parameters)

    def suggestions(self) -> list[str]:
        return ["What time is it?", "Open GitHub", "Create a note called ideas: Ship the capstone",
                "What is machine learning?", "List notes", "Tell me a joke",
                "Search the web for OpenCV face detection"]
