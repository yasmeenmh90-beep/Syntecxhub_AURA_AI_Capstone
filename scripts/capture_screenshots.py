#!/usr/bin/env python3
"""Render each GUI screen to docs/screenshots/*.png and the CLI to *.svg.

Everything runs in a temporary sandbox with a dry-run adapter: no camera, browser or real data.

    python scripts/capture_screenshots.py
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def seed_week(repo) -> None:
    """Sample history for the past 6 days so the dashboard has something to show (sandbox only)."""
    import random
    import uuid
    from datetime import datetime, timedelta

    from aura.commands.executor import ExecutionResult

    rng = random.Random(7)
    pool = [("get_time", "success")] * 5 + [("open_website", "success")] * 4 + \
           [("knowledge", "success")] * 3 + [("create_note", "success")] * 3 + \
           [("search_web", "success")] * 2 + [("search_web", "cancelled"), ("unknown_command", "rejected"),
                                              ("unknown_command", "rejected"), ("read_note", "error")]
    now = datetime.now().astimezone()
    for days_ago, count in zip(range(6, 0, -1), (4, 7, 3, 9, 6, 11), strict=True):
        day = now - timedelta(days=days_ago)
        for k in range(count):
            intent, status = rng.choice(pool)
            stamp = day.replace(hour=9 + k % 10, minute=rng.randrange(60)).isoformat(timespec="milliseconds")
            repo.record(ExecutionResult(str(uuid.uuid4()), intent, status, "sample", stamp, stamp))
        repo.record_session(day.isoformat(), "Face recognition" if days_ago % 3 else "Local PIN / password")


def main() -> int:
    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtWidgets import QApplication

    from aura.authentication.credentials import MemoryKeyring
    from aura.commands.platform_adapters import DryRunAdapter
    from aura.core.config import Config
    from aura.core.services import Services
    from aura.core.state import AuthMethod
    from aura.ui.main_window import MainWindow
    from aura.ui.theme import STYLESHEET

    out = ROOT / "docs" / "screenshots"
    out.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)

    def settle(ms=350):
        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec()

    with tempfile.TemporaryDirectory() as tmp:
        cfg = Config(Path(tmp), Config.load().models)
        services = Services.build(cfg, adapter=DryRunAdapter(), keyring_backend=MemoryKeyring())
        services.credentials.setup("demo-pin-1234")
        seed_week(services.repository)
        window = MainWindow(services)
        window.resize(1280, 820)
        window.show()
        settle()
        window.grab().save(str(out / "01-lock-screen.png"))

        window.assistant.unlock(AuthMethod.FACE)
        window.on_unlocked(AuthMethod.FACE)
        window.go(window.PAGE_ASSISTANT)
        page = window.assistant_page

        # Build up some history first (shown on the History page).
        bot = window.assistant
        for text, answer in (("System info", None), ("Search the web for OpenCV YuNet", True),
                             ("Launch the calculator", True), ("Tell me a joke", None),
                             ("Make me a sandwich", None), ("List notes", True)):
            reply = bot.handle(text)
            if reply.needs_confirmation:
                bot.confirm(answer)
        page.on_unlock()  # fresh chat transcript for the hero screenshot

        for text in ("Hey Aura, what time is it?", "What is machine learning?",
                     "Create a note called capstone: Demo on Friday!", "Open GitHub"):
            page.submit(text)
            settle(800)
        settle(1500)
        window.toast.hide()
        window.grab().save(str(out / "02-assistant.png"))

        window.resize(1280, 1240)  # tall enough to show the whole dashboard
        window.go(window.PAGE_DASHBOARD)
        settle(1800)  # let the count-ups and bar grow-ins finish
        window.grab().save(str(out / "00-dashboard.png"))
        window.resize(1280, 820)
        settle()

        window.go(window.PAGE_HISTORY)
        settle()
        window.grab().save(str(out / "03-history.png"))
        window.go(window.PAGE_SECURITY)
        settle()
        window.grab().save(str(out / "04-security.png"))
        window.close()

    capture_cli(out)
    print(f"Saved screenshots to {out}")
    return 0


def capture_cli(out: Path) -> None:
    from rich.console import Console

    from aura.authentication.credentials import MemoryKeyring
    from aura.cli import CLI, THEME
    from aura.commands.platform_adapters import DryRunAdapter
    from aura.core.config import Config
    from aura.core.services import Services
    from aura.core.state import AuthMethod

    with tempfile.TemporaryDirectory() as tmp:
        services = Services.build(Config(Path(tmp), Config.load().models), adapter=DryRunAdapter(),
                                  keyring_backend=MemoryKeyring())
        services.credentials.setup("demo-pin-1234")
        console = Console(theme=THEME, record=True, width=92, force_terminal=True, color_system="truecolor")
        CLI(services, console=console).banner()
        console.save_svg(str(out / "05-cli-doctor.svg"), title="python main.py doctor")

        console = Console(theme=THEME, record=True, width=92, force_terminal=True, color_system="truecolor")
        cli = CLI(services, console=console)
        cli.stage(1, "Authenticate")
        cli.assistant.unlock(AuthMethod.FACE)
        console.print("  [ok]✓ Face verified.[/]")
        cli.stage(2, "Command  ·  voice + text")
        for text in ("What time is it?", "Open GitHub", "What is machine learning?"):
            console.print(f"\n[brand]you ›[/] [user]{text}[/]")
            reply = cli.assistant.handle(text)
            if reply.needs_confirmation:
                console.print(f"  [warn]! {reply.text}[/] [muted]→ yes[/]")
                reply = cli.assistant.confirm(True)
            cli.show(reply)
        console.save_svg(str(out / "06-cli-session.svg"), title="python main.py cli --auth face --voice")


if __name__ == "__main__":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_SCALE_FACTOR", "2")  # Retina-sharp PNGs for the README
    raise SystemExit(main())
