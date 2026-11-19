from dataclasses import dataclass, field


@dataclass(frozen=True)
class IntentSpec:
    name: str
    examples: tuple[str, ...]
    patterns: tuple[str, ...]
    response: str
    permissions: tuple[str, ...] = ()
    handler: str = ""


@dataclass(frozen=True)
class Intent:
    name: str
    parameters: dict[str, str] = field(default_factory=dict)


INTENTS = (
    IntentSpec("greeting", ("Hello", "Hi Aura"), (r"(?:hello|hi|hey|good (?:morning|afternoon|evening))(?: there)?(?: aura)?",), "Hello. What can I help you do?"),
    IntentSpec("help", ("Help",), (r"help(?: me)?|what can you do|commands|show commands",), "Try: open YouTube, launch calculator, what time is it, create a note called ideas: My idea, list notes, or lock my assistant. I can also chat and explain AI topics (rules reused from the Week 2 chatbot): try “what is machine learning?” or “tell me a joke”."),
    IntentSpec("get_time", ("What time is it?",), (r"(?:what(?:'s| is)? )?(?:the )?(?:current )?time(?: is it)?(?: now| right now)?",
                                                   r"(?:tell me|give me|do you know) (?:the )?time"), "The time is {value}."),
    IntentSpec("get_date", ("Tell me today's date",), (r"(?:tell me |what(?:'s| is) )?(?:the |today's )?(?:current )?date(?: today)?",
                                                           r"what day is (?:it|today)(?: today)?|what is today"), "Today is {value}."),
    IntentSpec("system_information", ("System information",), (r"(?:show |get |tell me )?(?:the |my )?(?:basic )?system (?:information|info|details)",), "{value}"),
    IntentSpec("search_web", ("Search the web for Python tutorials",), (r"(?:search(?: the web)? for|google) (?P<query>.+)",), "Searching the web.", ("external",)),
    IntentSpec("open_website", ("Open YouTube", "Open GitHub"), (r"(?:open|go to|visit|launch) (?P<website>youtube|google|github|python)(?:\.(?:com|org))?",), "Opening {website}.", ("external",)),
    IntentSpec("open_application", ("Launch the calculator",), (r"(?:open|launch) (?:the )?(?P<application>calculator|text editor|editor)",), "Opening {application}.", ("external",)),
    IntentSpec("create_note", ("Create a note called meeting ideas: Discuss release",), (r"(?:create|save) (?:a )?note (?:called |named )?(?P<title>[^:]+?)(?::\s*(?P<body>.*))?",), "Note saved.", ("write_notes",)),
    IntentSpec("read_note", ("Read note meeting ideas",), (r"(?:read|show) (?:the )?note (?P<title>.+)",), "{value}", ("private",)),
    IntentSpec("list_notes", ("List notes",), (r"(?:list|show) (?:saved |my )?notes",), "{value}", ("private",)),
    IntentSpec("lock_assistant", ("Lock my assistant",), (r"lock(?: (?:my |the )?(?:assistant|aura))?",), "Session locked."),
    IntentSpec("exit_application", ("Exit Aura",), (r"(?:exit|quit|close)(?: aura| application)?",), "Goodbye.", ("confirm",)),
    IntentSpec("unknown_command", (), (), "I couldn't match that command. Type help to see supported commands."),
)
