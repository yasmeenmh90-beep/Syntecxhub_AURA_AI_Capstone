"""Reused Week 2 chatbot rules (aura/dialog/smalltalk.py)."""
import hashlib
import random

import pytest

from aura.dialog.smalltalk import DATA, SKIPPED_TAGS, SmallTalkResponder

bot = SmallTalkResponder(rng=random.Random(0))


@pytest.mark.parametrize("text, tag", [
    ("What is machine learning?", "knowledge"), ("explain RAG", "knowledge"),
    ("tell me a joke", "joke"), ("who are you", "bot_identity"), ("how are you", "how_are_you"),
    ("thanks!", "thanks"), ("I'm tired", "feeling_bad"), ("fun fact", "fun_fact"),
])
def test_week2_rules_answer(text, tag):
    assert bot.respond(text).tag == tag


@pytest.mark.parametrize("text", ["make me a sandwich", "open facebook", "", "bye"])
def test_no_match_returns_none(text):
    assert bot.respond(text) is None


def test_overlapping_and_misleading_tags_are_skipped():
    assert {i["tag"] for i in bot.intents}.isdisjoint(SKIPPED_TAGS)


def test_replies_are_rebranded_for_aura():
    texts = [r for i in bot.intents for r in i["responses"]]
    assert not any("NOVA" in t or "{name}" in t or "/topics" in t for t in texts)


# SHA-256 of week2/Project1/Syntecxhub_Rule_Based_Chatbot/data/*.json at the time they were copied.
# Pinned here (not read from ../../week2) so the guard runs in a standalone clone and in CI.
# If Week 2 is deliberately updated: re-copy the files, then update these hashes in the same commit.
WEEK2_SHA256 = {
    "week2_intents.json": "09047dd747e80f8a78c0fd7e41828d2a5c4db354e2cf89751b322fe0345ad101",
    "week2_knowledge_base.json": "c70649e574fd67af63dc863c35d5fbb53a1c564d2b470ae0b36b94fcad3039e2",
}


@pytest.mark.parametrize("name, expected", sorted(WEEK2_SHA256.items()))
def test_vendored_data_is_unchanged_week2_copy(name, expected):
    assert hashlib.sha256((DATA / name).read_bytes()).hexdigest() == expected
