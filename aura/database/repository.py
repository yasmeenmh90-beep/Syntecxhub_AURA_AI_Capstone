"""Short-lived SQLite connections permit worker access without sharing cursors."""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class Repository:
    def __init__(self, path: Path):
        self.path = path
        with self.connection() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version > 1:
                raise RuntimeError("Database is newer than this application; do not downgrade.")
            if version < 1:
                db.executescript("""
                    CREATE TABLE IF NOT EXISTS preferences(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                    CREATE TABLE IF NOT EXISTS history(
                        id TEXT PRIMARY KEY, intent TEXT, status TEXT, message TEXT,
                        started TEXT, completed TEXT, error TEXT);
                    CREATE TABLE IF NOT EXISTS notes(name TEXT PRIMARY KEY, updated TEXT);
                    CREATE TABLE IF NOT EXISTS shortcuts(phrase TEXT PRIMARY KEY, command TEXT NOT NULL);
                    CREATE TABLE IF NOT EXISTS sessions(started TEXT, method TEXT);
                    PRAGMA user_version=1;
                """)
        path.chmod(0o600)

    @contextmanager
    def connection(self):
        # `with sqlite3.connect()` only commits/rolls back; it never closes. Close explicitly.
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def get(self, key: str, default: Any = None) -> Any:
        with self.connection() as db:
            row = db.execute("SELECT value FROM preferences WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set(self, key: str, value: Any) -> None:
        with self.connection() as db:
            db.execute("INSERT OR REPLACE INTO preferences VALUES (?,?)", (key, json.dumps(value)))

    def record(self, result) -> None:
        with self.connection() as db:
            db.execute("INSERT INTO history VALUES (?,?,?,?,?,?,?)", (
                result.identifier, result.intent, result.status, result.message,
                result.started, result.completed, result.error))

    def history(self) -> list[dict]:
        with self.connection() as db:
            return [dict(r) for r in db.execute("SELECT * FROM history ORDER BY started DESC LIMIT 500")]

    def clear_history(self) -> None:
        with self.connection() as db:
            db.execute("DELETE FROM history")
        # VACUUM cannot run inside a transaction; it scrubs deleted rows from the file.
        db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        try:
            db.execute("VACUUM")
        finally:
            db.close()

    def shortcuts(self) -> dict[str, str]:
        with self.connection() as db:
            return dict(db.execute("SELECT phrase, command FROM shortcuts"))

    def save_shortcut(self, phrase: str, command: str) -> None:
        if not phrase.strip() or not command.strip() or max(len(phrase), len(command)) > 500:
            raise ValueError("A shortcut needs a phrase and command of at most 500 characters.")
        with self.connection() as db:
            db.execute("INSERT OR REPLACE INTO shortcuts VALUES (?,?)", (phrase.strip().lower(), command.strip()))

    def delete_shortcut(self, phrase: str) -> None:
        with self.connection() as db:
            db.execute("DELETE FROM shortcuts WHERE phrase=?", (phrase,))

    def note_metadata(self, name: str, updated: str) -> None:
        with self.connection() as db:
            db.execute("INSERT OR REPLACE INTO notes VALUES (?,?)", (name, updated))

    def record_session(self, started: str, method: str) -> None:
        with self.connection() as db:
            db.execute("INSERT INTO sessions VALUES (?,?)", (started, method))
