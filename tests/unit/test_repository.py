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
