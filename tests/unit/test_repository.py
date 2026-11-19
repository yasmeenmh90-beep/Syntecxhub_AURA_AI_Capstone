import sqlite3

import pytest

from aura.commands.executor import ExecutionResult
from aura.database.repository import Repository


def test_preferences_and_history(tmp_path):
    repo = Repository(tmp_path / "a.db")
    repo.set("k", {"x": 1})
    assert repo.get("k") == {"x": 1} and repo.get("missing", 7) == 7
    repo.record(ExecutionResult("1", "get_time", "success", "ok", "2026-01-01T00:00", "2026-01-01T00:00"))
    assert repo.history()[0]["intent"] == "get_time"
    repo.clear_history()
    assert repo.history() == []


def test_shortcuts(tmp_path):
    repo = Repository(tmp_path / "a.db")
    repo.save_shortcut("Code", "open github")
    assert repo.shortcuts() == {"code": "open github"}
    with pytest.raises(ValueError):
        repo.save_shortcut(" ", "x")


def test_refuses_newer_schema(tmp_path):
    path = tmp_path / "a.db"
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA user_version=9")
    with pytest.raises(RuntimeError, match="newer"):
        Repository(path)


def test_database_file_is_private(tmp_path):
    Repository(tmp_path / "a.db")
    assert oct((tmp_path / "a.db").stat().st_mode & 0o777) == "0o600"


def test_stats_aggregates(tmp_path):
    from datetime import datetime
    repo = Repository(tmp_path / "a.db")
    now = datetime.now().astimezone().isoformat()
    for i, (intent, status) in enumerate([("get_time", "success"), ("get_time", "success"),
                                          ("open_website", "confirmation_required"),
                                          ("open_website", "success"), ("unknown_command", "rejected")]):
        repo.record(ExecutionResult(str(i), intent, status, "m", now, now))
    repo.record_session(now, "Face recognition")
    repo.record_session(now, "Local PIN / password")
    s = repo.stats()
    assert s["total"] == 4                       # confirmation steps are not outcomes
    assert s["success_rate"] == 0.75
    assert s["intents"][0] == ("get_time", 2)
    assert s["days"][-1][1] == 4 and len(s["days"]) == 7
    assert (s["sessions"], s["face_sessions"]) == (2, 1)
    assert Repository(tmp_path / "b.db").stats()["success_rate"] is None
