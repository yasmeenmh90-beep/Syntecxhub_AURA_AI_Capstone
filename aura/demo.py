"""Reproducible, scripted end-to-end demo.

Runs the full pipeline in a throw-away data directory with a dry-run adapter, so it never opens
browsers, launches apps or touches your real notes/keychain. Use `--camera` to make stage 1 a
live face-presence check instead of demo authentication.
"""
from __future__ import annotations

import tempfile
import time
from pathlib import Path
from threading import Event

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from aura.authentication.credentials import MemoryKeyring
from aura.cli import CLI, THEME
from aura.commands.platform_adapters import DryRunAdapter
from aura.core.config import Config
from aura.core.services import Services
from aura.core.state import AuthMethod

SCRIPT = [
    "Hello Aura",
    "What time is it?",
    "Create a note called capstone demo: Face check, dialog and executor all working",
    "List notes",
    "Read note capstone demo",
    "Open GitHub",
    "Search the web for OpenCV YuNet face detection",
    "Launch the calculator",
    "What is machine learning?",
    "Tell me a joke",
    "Make me a sandwich",
    "Lock my assistant",
]


def run_demo(camera: bool = False, pause: float = 0.6, console: Console | None = None) -> int:
    console = console or Console(theme=THEME, highlight=False)
    with tempfile.TemporaryDirectory(prefix="aura-demo-") as tmp:
        base = Config.load()
        config = Config(Path(tmp), base.models, camera_index=base.camera_index)
        adapter = DryRunAdapter()
        services = Services.build(config, adapter=adapter, keyring_backend=MemoryKeyring())
        cli = CLI(services, console=console)
        cli.banner()

        cli.stage(1, "Authenticate")
        if camera:
            with console.status("[accent]Face presence check — look at the camera…") as spinner:
                message = services.auth.run("presence", Event(), lambda t: spinner.update(f"[accent]{t}"))
            cli.assistant.unlock(AuthMethod.PRESENCE)
            console.print(f"  [ok]✓ {message}[/]")
        else:
            cli.assistant.unlock(AuthMethod.DEMO)
            console.print("  [ok]✓ Demo session unlocked[/] [muted](pass --camera for a live face check)[/]")

        results = []
        cli.stage(2, "Command  →  3 · Act")
        for line in SCRIPT:
            time.sleep(pause)
            console.print(f"\n[brand]you ›[/] [user]{line}[/]")
            reply = cli.assistant.handle(line)
            if reply.needs_confirmation:
                console.print(f"  [warn]! {reply.text}[/] [muted]→ auto-confirming for the demo[/]")
                reply = cli.assistant.confirm(True)
            cli.show(reply)
            results.append((line, reply))

        table = Table(title="Demo summary", title_style="brand", border_style="#3b3f5c",
                      header_style="accent", expand=True)
        table.add_column("Command")
        table.add_column("Intent")
        table.add_column("Status")
        for line, reply in results:
            style = "ok" if reply.status in ("success", "locked") else "warn"
            table.add_row(line[:48], reply.intent, Text(reply.status, style=style))
        console.print(table)
        if adapter.actions:
            console.print(Panel("\n".join(f"{kind:<12} {target}" for kind, target in adapter.actions),
                                title="[accent]Actions captured by dry-run adapter[/]",
                                border_style="#3b3f5c"))
        ok = sum(r.status in ("success", "locked") for _, r in results)
        rejected = sum(r.status == "rejected" for _, r in results)
        reused = sum(r.intent == "knowledge" or r.intent.startswith("chat_") for _, r in results)
        console.print(f"\n[ok]Pipeline complete[/] — {ok} handled ({reused} answered by reused Week 2 rules), {rejected} rejected by design "
                      f"(unknown requests are never guessed at). Sandbox deleted; nothing on this machine changed.")
    return 0
