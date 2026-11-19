# Demo Script (≈ 6 minutes)

> The brief asks for **authenticate (face) → command → act**. Lead with the real face flow in the
> desktop app. `python main.py demo` is a reproducibility check: it unlocks in demo mode (or with a
> presence-only check via `--camera`), so it does **not** prove who you are.

## Rehearse once on the presenting machine (do not skip)
```bash
source .venv/bin/activate
python scripts/download_models.py     # face + voice models
python main.py doctor                 # every row green except "Face enrolled"
python main.py                        # create a PIN, then follow Part 1 once
```
Checklist (the automated tests use a fake camera, so the real hardware has only been tested by you):
- [ ] macOS asked for **camera** permission and you allowed it (System Settings → Privacy & Security → Camera)
- [ ] **Unlock with Face** succeeded at least once in the room's lighting
- [ ] macOS asked for **microphone** permission, and one spoken command (“what time is it”) was transcribed
- [ ] Browser opens on **Open GitHub → Confirm**

---

## Part 1: Face authentication, end to end (90 s) · the core of the brief
```bash
python main.py
```
1. Unlock with your **PIN**. Explain that it is the fallback and is stored as an Argon2 hash.
2. **Security & setup → Enroll my face.** Five samples are taken (`Capturing enrollment samples · 1/5 … 5/5`). Point out that only embeddings are stored, encrypted with a key in the OS keychain.
3. **Lock AURA** (button or ⌘L).
4. **Unlock with Face.** The scan line runs, a green box tracks your face, and the status counts `Checking identity · 1/4 … 4/4`. The sidebar shows *Face recognition* and the pill reads *Verified session*.
5. *Optional:* a colleague tries and it times out. Then show **Presence check**: it detects *a* face but not *whose*, so the session is flagged amber.

## Part 2: Voice + text commands (90 s)
1. Click 🎙 and say **"What time is it?"**. The orb turns cyan, the live transcript appears, and the answer comes back.
2. Type **"Create a note called demo day: Capstone presented!"**
3. **"List notes"** → Confirm, then **"Read note demo day"** → Confirm.
4. **"Open GitHub"** → Confirm. The browser opens.
5. **"What is machine learning?"** and **"Tell me a joke"** are answered by the **reused Week 2 chatbot rules**. Mention the reuse map.
6. **"Make me a sandwich"** is rejected, because AURA never guesses.

## Part 3: Audit & security (45 s)
* **History:** every command is listed with its status. Note bodies are never stored.
* **Security:** readiness checklist (including *Week 2 chatbot rules*) and *Delete enrollment*.

## Part 4: Reproducible run & CLI (60 s)
```bash
python main.py demo     # sandboxed scripted run: 12 commands, dry-run adapter, summary table
python main.py cli --auth face --voice
```
> "Same pipeline, different front-ends. The scripted demo is for reproducibility. It uses demo auth,
> which is why I showed real face unlock first."

## Talking points
* Three independent modules (**vision**, **dialog**, **executor**) joined by one `Assistant` class.
* Reuse: Week 2's rules and knowledge base run inside AURA. Week 3 vision and the NOVA voice module have defined plug-in points ([ARCHITECTURE.md#reuse-map](ARCHITECTURE.md#reuse-map)).
* Fully offline: OpenCV ONNX models, Vosk, SQLite.
* 120 automated tests, including GUI tests (the camera and microphone are faked in tests and were verified by hand in rehearsal).
* Known limitation: no liveness detection (a photo may pass). Next step: a blink or head-turn challenge.
