import numpy as np
import pytest
from rich.console import Console

from aura.app import build_parser
from aura.cli import CLI, THEME
from aura.core.config import Config
from aura.demo import run_demo


def test_scripted_demo_runs_end_to_end():
    console = Console(theme=THEME, record=True, width=110)
    assert run_demo(pause=0, console=console) == 0
    out = console.export_text()
    assert "Pipeline complete" in out and "https://github.com" in out and "calculator" in out


def test_cli_banner_lists_components(services):
    console = Console(theme=THEME, record=True, width=110)
    CLI(services, console=console).banner()
    out = console.export_text()
    for name in ("Dialog engine", "Face models", "Voice input", "PIN credential"):
        assert name in out


def test_cli_demo_auth_then_quit(services, monkeypatch):
    console = Console(theme=THEME, record=True, width=110)
    answers = iter(["What time is it?", "/history", "/quit"])
    monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *a, **k: next(answers))
    assert CLI(services, console=console).run("demo") == 0
    out = console.export_text()
    assert "The time is" in out and "get_time" in out


def test_parser_subcommands():
    parser = build_parser()
    assert parser.parse_args(["cli", "--auth", "pin"]).auth == "pin"
    assert parser.parse_args(["demo", "--fast"]).fast


real = Config.load()


@pytest.mark.skipif(not real.face_models_ready, reason="face models not downloaded")
def test_real_face_models_load_and_find_no_face_in_blank_frame():
    from aura.authentication.detector import FaceDetector
    detector = FaceDetector(real.models)
    blank = np.full((480, 640, 3), 128, dtype=np.uint8)
    assert len(detector.detect(blank)) == 0
    with pytest.raises(ValueError, match="No face"):
        detector.embedding(blank)


def test_presence_detector_loads_bundled_cascade():
    from aura.authentication.presence import PresenceDetector
    assert len(PresenceDetector().detect(np.zeros((480, 640, 3), dtype=np.uint8))) == 0


@pytest.mark.skipif(not real.voice_model_ready, reason="voice model not downloaded")
def test_vosk_model_loads():
    from aura.voice import SpeechRecognizer
    recognizer = SpeechRecognizer(real.vosk_model)
    assert recognizer.available and recognizer._load() is not None


@pytest.mark.parametrize("argv, speak", [([], False), (["gui"], False), (["gui", "--speak"], True)])
def test_main_without_subcommand_launches_gui(monkeypatch, tmp_path, argv, speak):
    import aura.app
    monkeypatch.setenv("AURA_DATA_DIR", str(tmp_path))
    calls = []
    monkeypatch.setattr(aura.app, "run_gui", lambda services, speak=False: calls.append(speak) or 0)
    assert aura.app.main(argv) == 0 and calls == [speak]
