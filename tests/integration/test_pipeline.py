"""End-to-end: authenticate (face / presence / PIN) → command → act, with fake hardware."""
from threading import Event

import numpy as np
import pytest

from aura.authentication.controller import AuthenticationController
from aura.core.assistant import Assistant
from aura.core.config import Config
from aura.core.state import AuthMethod
from tests.conftest import FakeCamera, FakeDetector


def test_full_pipeline_with_pin(services, adapter):
    bot = Assistant(services)
    assert bot.handle("what time is it").status == "locked"
    assert bot.unlock_with_pin("capstone-pin")           # first run creates the PIN
    assert bot.handle("What time is it?").status == "success"
    reply = bot.handle("Open GitHub")
    assert reply.needs_confirmation and "GitHub" in reply.text
    assert bot.handle("yes").status == "success"
    assert adapter.actions == [("website", "https://github.com")]
    assert bot.handle("search for cats").needs_confirmation
    assert bot.handle("no").status == "cancelled"
    assert len(adapter.actions) == 1
    assert bot.handle("lock").status == "locked" and not bot.unlocked
    assert not bot.unlock_with_pin("wrong-pin-123")


def test_new_command_abandons_pending_confirmation(services, adapter):
    bot = Assistant(services)
    bot.unlock(AuthMethod.DEMO)
    assert bot.handle("open youtube").needs_confirmation
    assert bot.handle("what time is it").status == "success"
    assert bot.confirm(True).status == "rejected" and adapter.actions == []


def test_shortcut_expands(services, adapter):
    bot = Assistant(services)
    bot.unlock(AuthMethod.DEMO)
    services.repository.save_shortcut("code time", "open github")
    assert bot.handle("Code time").intent == "open_website"


def test_exit_needs_confirmation(services):
    bot = Assistant(services)
    bot.unlock(AuthMethod.PIN)
    assert bot.handle("exit").needs_confirmation
    assert bot.handle("yes").status == "exit"


def test_face_enroll_then_verify(services):
    services.config.models.mkdir(parents=True, exist_ok=True)
    statuses = []
    assert services.auth.run("enroll", Event(), statuses.append) == "Enrollment complete"
    assert services.templates.enrolled and "5/5" in statuses[-1]
    assert services.auth.run("verify", Event(), statuses.append) == "Face verified"
    bot = Assistant(services)
    bot.unlock(AuthMethod.FACE)
    assert not services.session.demo


def test_face_verify_rejects_stranger(services):
    services.auth.run("enroll", Event(), lambda _s: None)
    stranger = np.zeros(128)
    stranger[1] = 1.0
    # Config is frozen, so build a short-timeout controller for the stranger.
    fast = Config(services.config.data, services.config.models, verification_timeout=0.6)
    ctrl = AuthenticationController(fast, services.templates, FakeCamera, lambda _m: FakeDetector(vectors=[stranger]))
    with pytest.raises(TimeoutError):
        ctrl.run("verify", Event(), lambda _s: None)


def test_verify_without_enrollment_is_explained(services):
    with pytest.raises(RuntimeError, match="No face is enrolled"):
        services.auth.run("verify", Event(), lambda _s: None)


def test_presence_check_and_low_assurance_flag(services):
    assert services.auth.run("presence", Event(), lambda _s: None) == "Face presence confirmed"
    Assistant(services).unlock(AuthMethod.PRESENCE)
    assert services.session.demo  # presence proves a face, not an identity


def test_cancel_stops_camera_loop(services):
    cancel = Event()
    cancel.set()
    with pytest.raises(RuntimeError, match="cancelled"):
        services.auth.run("presence", cancel, lambda _s: None)


def test_preview_receives_annotated_frames(services):
    frames = []
    services.auth.run("presence", Event(), lambda _s: None, frames.append)
    assert frames and frames[-1].shape == (480, 640, 3) and frames[-1].any()  # box drawn


def test_week2_fallback_answers_but_commands_win(services, adapter):
    bot = Assistant(services)
    bot.unlock(AuthMethod.DEMO)
    reply = bot.handle("What is machine learning?")
    assert reply.status == "success" and reply.intent == "knowledge" and "Machine Learning" in reply.text
    assert bot.handle("tell me a joke").intent == "chat_joke"
    assert bot.handle("open github").intent == "open_website"     # AURA command rules first
    assert bot.handle("make me a sandwich").status == "rejected"   # real unknowns still rejected
    assert services.repository.history()[0]["intent"] == "unknown_command"


def test_week2_fallback_can_be_disabled(config, adapter):
    from aura.authentication.credentials import MemoryKeyring
    from aura.core.services import Services
    s = Services.build(config, adapter=adapter, keyring_backend=MemoryKeyring(), smalltalk=False)
    bot = Assistant(s)
    bot.unlock(AuthMethod.DEMO)
    assert bot.handle("tell me a joke").status == "rejected"
