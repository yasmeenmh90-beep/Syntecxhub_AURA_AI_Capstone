"""Non-blocking text-to-speech. macOS uses the built-in `say`; other systems use pyttsx3."""
import platform
import shutil
import subprocess
import threading


class Speaker:
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self._process: subprocess.Popen | None = None
        self._lock = threading.Lock()

    def say(self, text: str) -> None:
        if not self.enabled or not text:
            return
        text = text[:400]
        self.stop()
        if platform.system() == "Darwin" and shutil.which("say"):
            with self._lock:
                self._process = subprocess.Popen(["say", text], stdout=subprocess.DEVNULL,
                                                 stderr=subprocess.DEVNULL)
            return
        threading.Thread(target=self._pyttsx3, args=(text,), daemon=True).start()

    @staticmethod
    def _pyttsx3(text: str) -> None:
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        except Exception:
            pass  # Speech is a convenience; the text reply is always shown.

    def stop(self) -> None:
        with self._lock:
            if self._process and self._process.poll() is None:
                self._process.terminate()
            self._process = None
