import os
import platform
import uuid
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlencode

from aura.commands.platform_adapters import PlatformAdapter
from aura.commands.validator import DISPLAY_NAMES, WEBSITES, note_path
from aura.dialog.intents import INTENTS


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


@dataclass(frozen=True)
class ExecutionResult:
    identifier: str
    intent: str
    status: str
    message: str
    started: str
    completed: str
    error: str = ""


class CommandExecutor:
    def __init__(self, config, repository, session, adapter=None):
        self.config, self.repo, self.session = config, repository, session
        self.adapter = adapter or PlatformAdapter()
        self.registry = {s.name: s for s in INTENTS}
        self.handlers = {
            "greeting": lambda _: self.registry["greeting"].response,
            "help": lambda _: self.registry["help"].response,
            "unknown_command": lambda _: self.registry["unknown_command"].response,
            "get_time": lambda _: datetime.now().strftime("The time is %I:%M %p."),
            "get_date": lambda _: datetime.now().strftime("Today is %A, %d %B %Y."),
            "system_information": lambda _: f"{platform.system()} {platform.release()} · {platform.machine()} · Python {platform.python_version()}",
            "open_website": self._website,
            "search_web": self._search,
            "open_application": self._application,
            "create_note": self._create_note,
            "read_note": self._read_note,
            "list_notes": self._list_notes,
            "lock_assistant": lambda _: "Session locked.",
            "exit_application": lambda _: "Goodbye.",
        }

    def requires_confirmation(self, intent) -> bool:
        spec = self.registry.get(intent.name)
        if spec is None:
            return False
        if any(p in spec.permissions for p in ("external", "private", "confirm")):
            return True
        if intent.name == "create_note":
            return note_path(self.config.notes, intent.parameters.get("title", "")).exists()
        return False

    def execute(self, intent, confirmed: bool = False) -> ExecutionResult:
        started = now()
        status, message, error = "success", "", ""
        try:
            if not self.session.authenticated:
                raise PermissionError("Unlock AURA before running commands.")
            if intent.name not in self.handlers:
                raise ValueError("Command is not registered.")
            if self.requires_confirmation(intent) and not confirmed:
                status, message = "confirmation_required", "Awaiting your confirmation."
            else:
                message = self.handlers[intent.name](intent.parameters)
                if intent.name == "unknown_command":
                    status = "rejected"
        except Exception as exc:
            status, message, error = "error", str(exc), type(exc).__name__
        result = ExecutionResult(str(uuid.uuid4()), intent.name, status, message, started, now(), error)
        # Never persist private note bodies, search queries, or raw user input.
        history_result = result
        if intent.name in {"read_note", "list_notes"} and status == "success":
            history_result = ExecutionResult(result.identifier, result.intent, result.status,
                                             "Private notes displayed (content not logged).",
                                             started, result.completed)
        self.repo.record(history_result)
        return result

    def _website(self, params):
        name = params["website"].lower()
        self.adapter.website(WEBSITES[name])
        return f"Opening {DISPLAY_NAMES.get(name, name)} in your default browser."

    def _search(self, params):
        query = params["query"].strip()
        if not query or len(query) > 500:
            raise ValueError("Search query must contain 1–500 characters.")
        self.adapter.website("https://www.google.com/search?" + urlencode({"q": query}))
        return f"Searching the web for “{query}”."

    def _application(self, params):
        name = params["application"].lower()
        self.adapter.application(name)
        return f"Launching the {'text editor' if name == 'editor' else name}."

    def _create_note(self, params):
        self.config.notes.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = note_path(self.config.notes, params["title"])
        body = params.get("body", "")
        if len(body) > 1600:
            raise ValueError("Note content is limited to 1,600 characters.")
        # O_NOFOLLOW prevents a replaced final symlink from being followed on Unix.
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            file.write(body)
        self.repo.note_metadata(path.stem, now())
        return f"Saved note ‘{path.stem}’."

    def _read_note(self, params):
        path = note_path(self.config.notes, params["title"])
        if not path.is_file():
            raise FileNotFoundError(f"No note called ‘{params['title']}’. Say “list notes” to see them.")
        if path.stat().st_size > 10_000:
            raise ValueError("Note is too large to display.")
        return path.read_text(encoding="utf-8") or "This note is empty."

    def _list_notes(self, _):
        self.config.notes.mkdir(parents=True, exist_ok=True, mode=0o700)
        names = sorted(p.stem for p in self.config.notes.glob("*.txt") if not p.is_symlink())
        return "Saved notes: " + ", ".join(names) if names else "No saved notes yet."
