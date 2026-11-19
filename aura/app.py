"""Command-line entry point.

    python main.py                 # desktop GUI (default)
    python main.py cli             # terminal assistant (choose auth method interactively)
    python main.py cli --auth pin  # skip the menu
    python main.py demo            # scripted, reproducible end-to-end demo (dry run)
    python main.py doctor          # readiness check
    python main.py enroll          # enroll your face from the terminal (PIN required)
"""
from __future__ import annotations

import argparse
import sys

from aura import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aura-ai", description="AURA — authenticate, command, act.",
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=__doc__.split("\n", 2)[2])
    parser.add_argument("--version", action="version", version=f"AURA {__version__}")
    # `python main.py` (no subcommand) runs the GUI, so subcommand options need top-level defaults.
    parser.set_defaults(speak=False, voice=False, auth=None, camera=False, fast=False)
    sub = parser.add_subparsers(dest="command")

    gui = sub.add_parser("gui", help="launch the desktop app (default)")
    gui.add_argument("--speak", action="store_true", help="read replies aloud")

    cli = sub.add_parser("cli", help="run the terminal assistant")
    cli.add_argument("--auth", choices=["face", "pin", "presence", "demo"], help="authentication method")
    cli.add_argument("--voice", action="store_true", help="enable microphone input (Enter = listen)")
    cli.add_argument("--speak", action="store_true", help="read replies aloud")

    demo = sub.add_parser("demo", help="scripted end-to-end demo in a temporary sandbox")
    demo.add_argument("--camera", action="store_true", help="use a live face-presence check for stage 1")
    demo.add_argument("--fast", action="store_true", help="no pauses between steps")

    sub.add_parser("doctor", help="show component readiness")
    sub.add_parser("enroll", help="enroll your face from the terminal")
    return parser


def run_gui(services, speak: bool = False) -> int:
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication

    from aura.ui.main_window import MainWindow
    from aura.ui.theme import STYLESHEET

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("AURA")
    app.setApplicationDisplayName("AURA")
    font = QFont(app.font())
    font.setPointSize(13 if sys.platform == "darwin" else 10)
    app.setFont(font)
    app.setStyleSheet(STYLESHEET)
    window = MainWindow(services, speak=speak)
    window.show()
    return app.exec()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    command = args.command or "gui"

    if command == "demo":
        from aura.demo import run_demo
        return run_demo(camera=args.camera, pause=0 if args.fast else 0.6)

    from aura.core.services import Services
    try:
        services = Services.build()
    except Exception as exc:  # noqa: BLE001 - e.g. unreadable data dir, newer DB schema
        print(f"AURA could not start: {exc}", file=sys.stderr)
        return 2

    if command == "gui":
        return run_gui(services, speak=args.speak)
    from aura import cli
    if command == "cli":
        return cli.CLI(services, voice=args.voice, speak=args.speak).run(args.auth)
    if command == "doctor":
        return cli.doctor(services)
    if command == "enroll":
        return cli.enroll(services)
    return 1


if __name__ == "__main__":
    sys.exit(main())
