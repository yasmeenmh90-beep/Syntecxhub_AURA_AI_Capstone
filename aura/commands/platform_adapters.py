import platform
import shutil
import subprocess
import webbrowser

from aura.commands.validator import safe_url


class PlatformAdapter:
    def __init__(self, system=None, runner=subprocess.run, browser=webbrowser.open):
        self.system = system or platform.system()
        self.runner, self.browser = runner, browser

    def website(self, url: str) -> None:
        if not self.browser(safe_url(url)):
            raise RuntimeError("The default browser did not accept the request.")

    def application(self, name: str) -> None:
        name = name.lower()
        if name == "editor":
            name = "text editor"
        approved = {
            "Darwin": {"calculator": ["/usr/bin/open", "-a", "Calculator"],
                       "text editor": ["/usr/bin/open", "-a", "TextEdit"]},
            "Windows": {"calculator": ["calc.exe"], "text editor": ["notepad.exe"]},
            "Linux": {"calculator": ["gnome-calculator"], "text editor": ["gedit"]},
        }
        args = approved.get(self.system, {}).get(name)
        if not args:
            raise ValueError("Application is not approved or this operating system is unsupported.")
        if not shutil.which(args[0]):
            raise RuntimeError(f"Approved application launcher {args[0]} is not installed.")
        # Windows/Linux GUI programs may remain running: Popen avoids waiting for their exit.
        if self.system == "Darwin":
            self.runner(args, check=True, timeout=10, capture_output=True, shell=False)
        elif self.runner is not subprocess.run:
            self.runner(args, check=True, timeout=10, shell=False)
        else:
            subprocess.Popen(args, shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class DryRunAdapter:
    """Records actions instead of performing them — used by `aura-ai demo` and the tests.

    It still runs the same URL/application validation as the real adapter, so a dry run
    proves that a command *would* be allowed.
    """

    def __init__(self, system=None):
        self.system = system or platform.system()
        self.actions: list[tuple[str, str]] = []

    def website(self, url: str) -> None:
        self.actions.append(("website", safe_url(url)))

    def application(self, name: str) -> None:
        name = "text editor" if name.lower() == "editor" else name.lower()
        if name not in {"calculator", "text editor"}:
            raise ValueError("Application is not approved or this operating system is unsupported.")
        self.actions.append(("application", name))
