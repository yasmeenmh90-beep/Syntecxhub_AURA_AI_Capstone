import re

from aura.dialog.intents import INTENTS, Intent


class DialogEngine:
    def match(self, text: str) -> Intent:
        if not isinstance(text, str) or not text.strip() or len(text) > 2000 or "\x00" in text:
            return Intent("unknown_command")
        # Keep payload case for notes and searches; match with case-insensitive patterns.
        cleaned = text.strip()
        # Strip a wake word and politeness so "Hey Aura, could you please open GitHub?" works.
        cleaned = re.sub(r"^(?:(?:hey|ok|okay) aura[,!.]?\s+)", "", cleaned, flags=re.I)
        cleaned = re.sub(r"^(?:(?:can|could|would|will) you |please )+", "", cleaned, flags=re.I)
        verbatim = cleaned.strip()  # Note bodies keep their punctuation exactly as typed.
        cleaned = re.sub(r"[?.!\s]+$", "", cleaned)
        cleaned = re.sub(r"\s+please$", "", cleaned, flags=re.I).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        for spec in INTENTS:
            candidates = (verbatim, cleaned) if spec.name == "create_note" else (cleaned,)
            for pattern in spec.patterns:
                match = next((m for c in candidates if (m := re.fullmatch(pattern, c, flags=re.I))), None)
                if match:
                    parameters = {k: (v or "").strip() for k, v in match.groupdict().items()}
                    return Intent(spec.name, parameters)
        return Intent("unknown_command")
