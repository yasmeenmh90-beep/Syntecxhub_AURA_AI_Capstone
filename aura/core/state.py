"""Session and assistant state shared by the CLI and the GUI (no UI imports)."""
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class AssistantState(StrEnum):
    IDLE = "Idle"
    LISTENING = "Listening"
    PROCESSING = "Processing"
    SPEAKING = "Speaking"
    SUCCESS = "Success"
    ERROR = "Error"
    LOCKED = "Locked"


class AuthMethod(StrEnum):
    """How the current session was unlocked. Values are shown to the user."""
    FACE = "Face recognition"
    PIN = "Local PIN / password"
    PRESENCE = "Face presence · detection only"
    DEMO = "DEMO · no identity verification"


#: Methods that do not prove *who* the user is. The UI flags these sessions.
LOW_ASSURANCE = {AuthMethod.PRESENCE, AuthMethod.DEMO}


@dataclass
class Session:
    authenticated: bool = False
    demo: bool = False
    method: str = "Locked"
    started: str = ""

    def unlock(self, method: str) -> None:
        self.authenticated = True
        self.demo = method in LOW_ASSURANCE
        self.method = str(method)
        self.started = datetime.now().astimezone().isoformat(timespec="seconds")

    def lock(self) -> None:
        self.authenticated = False
        self.demo = False
        self.method = "Locked"
        self.started = ""
