"""Composition root: builds every service once so CLI, GUI and tests share the same wiring.

Swap any component (camera, detector, adapter, keyring backend) by passing it in — this is the
seam that lets later projects reuse AURA's modules independently.
"""
from dataclasses import dataclass, field

from aura.authentication.controller import AuthenticationController
from aura.authentication.credentials import Credentials, TemplateStore
from aura.commands.executor import CommandExecutor
from aura.core.config import Config
from aura.core.state import Session
from aura.database.repository import Repository
from aura.dialog.engine import DialogEngine
from aura.dialog.smalltalk import SmallTalkResponder


@dataclass
class Services:
    config: Config
    repository: Repository
    credentials: Credentials
    templates: TemplateStore
    session: Session
    dialog: DialogEngine
    executor: CommandExecutor
    auth: AuthenticationController
    smalltalk: SmallTalkResponder | None = None  # Week 2 chatbot rules (fallback)
    extras: dict = field(default_factory=dict)

    @classmethod
    def build(cls, config: Config | None = None, *, adapter=None, keyring_backend=None,
              camera_factory=None, detector_factory=None, presence_factory=None,
              smalltalk: SmallTalkResponder | None | bool = True) -> "Services":
        config = config or Config.load()
        config.prepare()
        repository = Repository(config.database)
        templates = (TemplateStore(config.data, keyring_backend) if keyring_backend
                     else TemplateStore(config.data))
        session = Session()
        auth_kwargs = {k: v for k, v in {"camera_factory": camera_factory,
                                         "detector_factory": detector_factory,
                                         "presence_factory": presence_factory}.items() if v}
        return cls(
            config=config,
            repository=repository,
            credentials=Credentials(repository),
            templates=templates,
            session=session,
            dialog=DialogEngine(),
            executor=CommandExecutor(config, repository, session, adapter),
            auth=AuthenticationController(config, templates, **auth_kwargs),
            smalltalk=SmallTalkResponder() if smalltalk is True else (smalltalk or None),
        )

    def readiness(self) -> dict[str, tuple[bool, str]]:
        """Human-readable component checklist used by `doctor`, the CLI banner and the GUI."""
        from aura.voice.stt import SpeechRecognizer
        cfg = self.config
        return {
            "Dialog engine": (True, "Rule-based intents loaded"),
            "Command executor": (True, "Allow-listed actions only"),
            "Week 2 chatbot rules": (self.smalltalk is not None,
                                     self.smalltalk.summary if self.smalltalk else "Disabled"),
            "PIN credential": (self.credentials.configured,
                               "Configured" if self.credentials.configured else "Not set — created on first unlock"),
            "Face models": (cfg.face_models_ready,
                            "YuNet + SFace ready" if cfg.face_models_ready else "Missing — run scripts/download_models.py"),
            "Face enrolled": (self.templates.enrolled,
                              "Encrypted template stored" if self.templates.enrolled else "Not enrolled"),
            "Presence check": (True, "OpenCV Haar cascade (bundled)"),
            "Voice input": (SpeechRecognizer.dependencies_ok() and cfg.voice_model_ready,
                            "Vosk offline model ready" if cfg.voice_model_ready else "Model missing — text input still works"),
        }
