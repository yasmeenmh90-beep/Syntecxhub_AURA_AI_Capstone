# Project Status — brief vs. delivery

| Brief requirement | Status | Where |
|---|---|---|
| Rule-based dialog | ✅ Complete | `aura/dialog/` — 13 intents, wake-word & politeness stripping, parameter extraction |
| Small vision check (face detection) | ✅ Complete | `aura/authentication/` — YuNet detection + SFace recognition; Haar presence check (no download) |
| Command executor | ✅ Complete | `aura/commands/` — allow-listed handlers, confirmation gate, audit log, dry-run adapter |
| CLI **or** minimal GUI | ✅ Both | `aura/cli.py` (rich) and `aura/ui/` (PySide6) |
| Sequence: authenticate (face) → voice/text command → act | ✅ Complete | `aura/core/assistant.py`, shared by GUI, CLI and demo |
| Modular design so interns can reuse earlier projects' code | ✅ Reusable design · ✅ Week 2 reused | **Integrated:** Week 2 chatbot intents + knowledge base (copied unchanged, matcher ported) answer non-command input. **Plug-in points only (not integrated):** Week 3 face/gesture, NOVA voice. See [ARCHITECTURE.md#reuse-map](ARCHITECTURE.md#reuse-map) |
| Short demo script | ✅ Complete | `docs/DEMO_SCRIPT.md` leads with real face unlock in the GUI. `python main.py demo` is a sandboxed reproducibility run using demo/presence auth, **not** face identity |
| README for reproducibility | ✅ Complete | `README.md`, `docs/INSTALLATION.md`, pinned `requirements.txt`, `scripts/download_models.py` |
| Tests | ✅ 120 passing (camera/mic faked) | `tests/unit`, `tests/integration`, `tests/gui` |

## Work done
* Reuse pass: integrated Week 2 chatbot rules (`aura/dialog/smalltalk.py`), added the reuse map, put real face auth first in the demo script.
* Added the missing entry point `aura/app.py` (`main.py` previously crashed on import).
* Built: pipeline orchestrator, services container, voice STT/TTS, presence check, model downloader,
  rich CLI, scripted demo, full PySide6 GUI (lock screen, assistant, history, security), tests, docs.
* Fixed bugs in the existing code:
  * "What time is it?" was not recognised (regex required "what's"/"what is").
  * `Repository.clear_history()` crashed (`VACUUM` inside a transaction).
  * SQLite connections were never closed (`with sqlite3.connect()` doesn't close).
  * Reading a missing note surfaced a raw `[Errno 2]` message.
  * `vosk==0.3.45` has no macOS wheel → pinned `0.3.44`.

## Verification gaps (do before submitting)
* The real webcam and microphone are **not** covered by automated tests (they use a fake camera). Run the
  rehearsal checklist in DEMO_SCRIPT.md once: face unlock + one spoken command, and grant the macOS permissions.

## Known limitations / possible next steps
* Week 2 rules search *anywhere* in a sentence, while AURA commands must match the whole sentence. So a mixed
  sentence like “open facebook and tell me a joke” gets the joke instead of a rejection. Harmless, but
  don't improvise mixed sentences in the live demo.
* No liveness / anti-spoofing (a photo may pass face verification) → add blink or head-turn challenge.
* English-only voice model; swap `AURA_VOSK_MODEL` for other languages.
* Small fixed allow-list of sites/apps; shortcut phrases exist in the database but have no UI editor yet.
