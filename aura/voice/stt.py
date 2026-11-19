"""Offline speech-to-text with Vosk + sounddevice.

Everything is imported lazily so the rest of AURA (and the tests) work on machines without a
microphone, PortAudio or the Vosk model. Text input is always available as the fallback.
"""
import json
import queue
import time
from collections.abc import Callable
from pathlib import Path
from threading import Event


class VoiceUnavailable(RuntimeError):
    pass


class SpeechRecognizer:
    sample_rate = 16000

    def __init__(self, model_dir: Path):
        self.model_dir = Path(model_dir)
        self._model = None

    @staticmethod
    def dependencies_ok() -> bool:
        try:
            import sounddevice  # noqa: F401
            import vosk  # noqa: F401
        except Exception:  # PortAudio missing raises OSError, not ImportError
            return False
        return True

    @property
    def available(self) -> bool:
        return self.dependencies_ok() and self.model_dir.is_dir()

    def _load(self):
        if self._model is None:
            if not self.model_dir.is_dir():
                raise VoiceUnavailable("Voice model missing. Run `python scripts/download_models.py --voice`.")
            try:
                import vosk
            except Exception as exc:
                raise VoiceUnavailable(f"Vosk is not installed: {exc}") from exc
            vosk.SetLogLevel(-1)
            self._model = vosk.Model(str(self.model_dir))
        return self._model

    def listen(self, cancel: Event | None = None, timeout: float = 8.0, silence: float = 1.4,
               on_partial: Callable[[str], None] = lambda _t: None) -> str:
        """Record until the speaker pauses, `timeout` elapses, or `cancel` is set."""
        import vosk
        try:
            import sounddevice as sd
        except Exception as exc:
            raise VoiceUnavailable(f"Microphone backend unavailable: {exc}") from exc
        cancel = cancel or Event()
        recognizer = vosk.KaldiRecognizer(self._load(), self.sample_rate)
        chunks: queue.Queue[bytes] = queue.Queue()
        heard, last_change, last_partial = "", time.monotonic(), ""
        start = time.monotonic()
        try:
            with sd.RawInputStream(samplerate=self.sample_rate, blocksize=4000, dtype="int16",
                                   channels=1, callback=lambda data, *_: chunks.put(bytes(data))):
                while not cancel.is_set():
                    now = time.monotonic()
                    if now - start > timeout:
                        break
                    if heard and now - last_change > silence:
                        break
                    try:
                        data = chunks.get(timeout=0.2)
                    except queue.Empty:
                        continue
                    if recognizer.AcceptWaveform(data):
                        text = json.loads(recognizer.Result()).get("text", "")
                        if text:
                            heard = f"{heard} {text}".strip()
                            last_change = time.monotonic()
                            on_partial(heard)
                    else:
                        partial = json.loads(recognizer.PartialResult()).get("partial", "")
                        if partial and partial != last_partial:
                            last_partial, last_change = partial, time.monotonic()
                            on_partial(f"{heard} {partial}".strip())
        except sd.PortAudioError as exc:
            raise VoiceUnavailable(f"Microphone unavailable — check OS permission: {exc}") from exc
        final = json.loads(recognizer.FinalResult()).get("text", "")
        return f"{heard} {final}".strip()
