"""Small-talk and AI-knowledge fallback, reused from Week 2's rule-based chatbot.

Reuse, concretely:
* `data/week2_intents.json` and `data/week2_knowledge_base.json` are copied byte-for-byte from
  week2/Project1/Syntecxhub_Rule_Based_Chatbot/data/.
* `normalize`, `match_intent` and `match_knowledge` are ported from that project's `ChatEngine`
  (chatbot.py). They are ported rather than imported because chatbot.py imports its LLM client
  and rich UI at module level, which AURA must not depend on.

AURA's command rules always run first. This responder is only asked when no command matched,
so "open GitHub" can never be swallowed by small talk, and real unknowns are still rejected.
"""
from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from pathlib import Path

DATA = Path(__file__).with_name("data")

# Week 2 tags that AURA already handles as commands, or that would mislead here:
# help/time/date → AURA intents; farewell → AURA's exit (with confirmation);
# creator → says "Project 1", which is wrong for this project.
SKIPPED_TAGS = {"help", "time", "date", "farewell", "creator"}


@dataclass(frozen=True)
class ChatAnswer:
    tag: str      # Week 2 intent tag, or "knowledge"
    text: str
    topic: str = ""


class SmallTalkResponder:
    def __init__(self, intents_path: Path = DATA / "week2_intents.json",
                 kb_path: Path = DATA / "week2_knowledge_base.json", rng: random.Random | None = None):
        self.rng = rng or random.Random()
        raw = json.loads(intents_path.read_text(encoding="utf-8"))["intents"]
        self.intents = []
        for intent in raw:
            if intent["tag"] in SKIPPED_TAGS:
                continue
            responses = [self._adapt(r) for r in intent["responses"]]
            # Drop replies that point at Week 2-only features (/topics, saved transcripts).
            responses = [r for r in responses if "/topics" not in r and "saved" not in r] or responses
            self.intents.append({"tag": intent["tag"], "responses": responses,
                                 "compiled": [re.compile(p, re.I) for p in intent["patterns"]]})
        self.topics = json.loads(kb_path.read_text(encoding="utf-8"))["topics"]

    @staticmethod
    def _adapt(reply: str) -> str:
        """Week 2's bot was called NOVA and personalised replies with {name}."""
        return reply.replace("{name}", "").replace("NOVA", "AURA")

    # ── Ported from Week 2 ChatEngine ────────────────────────────────────
    @staticmethod
    def normalize(text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[^\w\s'\-?]", " ", text)
        return re.sub(r"\s+", " ", text)

    def match_intent(self, text: str):
        for intent in self.intents:
            if any(p.search(text) for p in intent["compiled"]):
                return intent
        return None

    def match_knowledge(self, text: str):
        """Score each topic by keyword hits; longer keywords weigh more."""
        best, best_score = None, 0.0
        for topic in self.topics:
            score = 0.0
            for kw in topic["keywords"]:
                if re.search(rf"\b{re.escape(kw)}\b", text):
                    score += len(kw.split()) * 2 + len(kw) / 10
            if score > best_score:
                best, best_score = topic, score
        return best

    # ── AURA entry point ─────────────────────────────────────────────────
    def respond(self, message: str) -> ChatAnswer | None:
        text = self.normalize(message or "")
        if not text:
            return None
        topic = self.match_knowledge(text)
        if topic:  # Week 2 rule: knowledge answers win over small talk.
            return ChatAnswer("knowledge", topic["answer"], topic["topic"])
        intent = self.match_intent(text)
        if intent:
            return ChatAnswer(intent["tag"], self.rng.choice(intent["responses"]))
        return None

    @property
    def summary(self) -> str:
        return f"{len(self.intents)} small-talk intents + {len(self.topics)} AI topics (Week 2)"
