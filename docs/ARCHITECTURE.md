# Architecture

## Design goals
1. **Modular.** Each stage is a package with a narrow interface, so interns can lift one out and reuse it.
2. **UI-agnostic core.** Nothing under `authentication/`, `dialog/`, `commands/`, `voice/` or `core/` imports Qt.
3. **Offline and private.** No cloud calls. Biometrics are encrypted, and private content is never logged.
4. **Testable.** Hardware (camera, detector, browser, keychain) is injected, so tests run headless.

## Module map

| Package | Public interface | Notes |
|---|---|---|
| `core.config` | `Config.load()`, `.prepare()` | Paths and thresholds; environment overrides |
| `core.services` | `Services.build(config, adapter=…, keyring_backend=…, camera_factory=…, detector_factory=…)` | Composition root and `readiness()` |
| `core.assistant` | `Assistant.unlock*()`, `.handle(text) -> Reply`, `.confirm(bool)` | **The pipeline** |
| `authentication.controller` | `run(mode, cancel, status_cb, preview_cb)` where mode is `enroll`, `verify` or `presence` | Camera loop |
| `authentication.detector` | `FaceDetector.detect(frame)`, `.embedding(frame, faces)` | YuNet + SFace with quality gates |
| `authentication.presence` | `PresenceDetector.detect(frame)`, `PresenceService.check(n)` | Haar cascade; detection only |
| `authentication.credentials` | `Credentials`, `TemplateStore`, `MemoryKeyring` | Argon2 + Fernet/keyring |
| `dialog.engine` | `DialogEngine.match(text) -> Intent` | Ordered regex rules from `intents.py` |
| `commands.executor` | `CommandExecutor.execute(intent, confirmed) -> ExecutionResult` | Auth check, confirmation gate, audit |
| `commands.platform_adapters` | `PlatformAdapter`, `DryRunAdapter` | Opens the browser or approved apps |
| `voice` | `SpeechRecognizer.listen()`, `Speaker.say()` | Lazy imports; degrade gracefully |
| `database.repository` | `Repository` | SQLite with short-lived connections; schema `user_version=1` |

## Pipeline sequence

```
User        UI (Qt/CLI)        Assistant         AuthController     Dialog      Executor      Adapter
 │  face  ──▶ CameraWorker ───────────────────▶ run("verify") ─▶ frames ⟲ (4 consecutive matches)
 │                 ◀── "Face verified" ─────────┘
 │                 └─▶ unlock(FACE) ──▶ Session.authenticated = True
 │ "open github" ─▶ handle(text) ─────────────────────────────▶ match ─▶ Intent(open_website)
 │                                   └─────────────────────────────────────▶ execute()
 │                 ◀── Reply(confirmation_required) ◀──────────────────────┘
 │ Confirm ──────▶ confirm(True) ──────────────────────────────────────────▶ execute(confirmed) ─▶ website()
 │                 ◀── Reply(success) ─── history row written (no private text)
```

## Key decisions

| Decision | Why |
|---|---|
| YuNet + SFace over `face_recognition`/dlib | Ships with `opencv-python`; no C++ build step; small models |
| Median of cosine scores across 5 enrolled samples, 4 consecutive frames | Resists a single lucky frame or an outlier reference |
| A presence-only mode, clearly labelled | Meets the brief's "small vision check (face detection)" with zero downloads, without pretending to verify identity |
| Regex rule engine | Deterministic, explainable, trivially testable; fits "rule-based dialog" |
| Confirmation gate in the executor (not the UI) | Every front-end gets the same safety guarantees |
| `DryRunAdapter` | Reproducible demos and tests that still exercise URL and app validation |
| Worker `QThread`s | The camera, the microphone and slow commands never block the UI |

## Extending
* **New command:** add an `IntentSpec(name, examples, patterns, response, permissions)` and a handler entry in `CommandExecutor.handlers`. Add `"external"` or `"private"` to `permissions` to require confirmation.
* **New front-end** (for example web or Telegram): build `Services`, wrap them in `Assistant`, then call `handle()` and `confirm()`.
* **Different recognizer:** implement `detect(frame)` and `embedding(frame, faces)`, then pass `detector_factory=` to `Services.build`.

## Reuse map

Which earlier Syntecxhub projects plug into which part of AURA, and what is **actually integrated** today.

| Earlier project | AURA seam | Status | What exactly |
|---|---|---|---|
| Week 2 · *Syntecxhub_Rule_Based_Chatbot* | `dialog/smalltalk.py` → `Assistant` fallback | **Integrated** | `intents.json` and `knowledge_base.json` copied unchanged to `aura/dialog/data/week2_*.json`. `normalize`, `match_intent` and `match_knowledge` ported from `ChatEngine`, which can't be imported directly because `chatbot.py` loads its LLM client and UI on import. 8 small-talk intents + 15 AI topics. Tags that clash with AURA commands (help/time/date/farewell) or describe the wrong project (creator) are skipped, and “NOVA” becomes “AURA”. `test_vendored_data_matches_week2_source` fails if the copy drifts. |
| Week 3 · *Syntecxhub_Face_Recognition* | `Services.build(detector_factory=…)` | Plug-in point (same approach) | Uses the same YuNet + SFace + Haar stack as `aura/authentication`. An adapter exposing `detect(frame) -> (N,≥4) array` and `embedding(frame, faces)` would replace AURA's detector. Not wired in: AURA's detector adds quality gates (size, light, blur) that Week 3 does not have. |
| Week 3 · *Syntecxhub_Hand_Gesture_Recognition* | second vision check after face unlock, or `presence_factory=` | Plug-in point | A thumbs-up confirmation gesture could replace the Confirm button. Not integrated because it needs MediaPipe (a large extra dependency) and its own model download. |
| Week 4 · *NOVA_Voice_Assistant* (`backend/speech.py`, `tts.py`) | `voice.SpeechRecognizer.listen()`, `voice.Speaker.say()` | Plug-in point | NOVA uses `SpeechRecognition` (online-capable). AURA keeps Vosk so the whole pipeline stays offline. Either can sit behind the same two methods. |

**How to plug one in:** write a class with the interface in the "AURA seam" column, then pass it to `Services.build(...)` or set it on the `Services` object. No UI code changes are needed, because the GUI, CLI and demo all go through `Assistant`.
