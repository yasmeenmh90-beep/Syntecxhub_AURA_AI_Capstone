import pytest

from aura.dialog.engine import DialogEngine

engine = DialogEngine()


@pytest.mark.parametrize("text, intent", [
    ("Hello", "greeting"), ("Hey Aura", "greeting"), ("Good evening Aura", "greeting"),
    ("help", "help"), ("What can you do?", "help"),
    ("What time is it?", "get_time"), ("what's the time", "get_time"), ("tell me the time", "get_time"),
    ("What day is it?", "get_date"), ("Tell me today's date", "get_date"),
    ("system info", "system_information"), ("Show system information", "system_information"),
    ("Open YouTube", "open_website"), ("visit github.com", "open_website"),
    ("Search the web for python tutorials", "search_web"), ("google cats", "search_web"),
    ("Launch the calculator", "open_application"), ("open text editor", "open_application"),
    ("list notes", "list_notes"), ("show my notes", "list_notes"),
    ("read note ideas", "read_note"), ("lock my assistant", "lock_assistant"), ("quit", "exit_application"),
    ("make me a sandwich", "unknown_command"), ("", "unknown_command"), ("open facebook", "unknown_command"),
])
def test_intent_matching(text, intent):
    assert engine.match(text).name == intent


def test_wake_word_and_politeness_are_stripped():
    intent = engine.match("Hey Aura, could you please open GitHub?")
    assert intent.name == "open_website"
    assert intent.parameters["website"].lower() == "github"


def test_note_parameters_keep_case_and_punctuation():
    intent = engine.match("Create a note called Meeting Ideas: Ship it Friday!")
    assert intent.parameters == {"title": "Meeting Ideas", "body": "Ship it Friday!"}


def test_search_query_extracted():
    assert engine.match("search for OpenCV face detection please").parameters["query"] == "OpenCV face detection"


@pytest.mark.parametrize("bad", [None, 42, "x" * 2001, "hello\x00"])
def test_invalid_input_is_unknown(bad):
    assert engine.match(bad).name == "unknown_command"
