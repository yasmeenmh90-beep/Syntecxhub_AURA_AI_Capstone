"""Argon2 credentials and encrypted embeddings; no plaintext key fallback."""
import json
import os
import time
from pathlib import Path

import keyring
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from cryptography.fernet import Fernet


class Credentials:
    def __init__(self, repository):
        self.repo = repository
        self.hasher = PasswordHasher()

    @property
    def configured(self) -> bool:
        return bool(self.repo.get("credential_hash"))

    def setup(self, password: str) -> None:
        if self.configured:
            raise ValueError("A credential already exists. Unlock before changing it.")
        if len(password) < 8 or len(password) > 256:
            raise ValueError("Use 8–256 characters (a PIN must contain at least 8 digits).")
        self.repo.set("credential_hash", self.hasher.hash(password))
        self.repo.set("auth_failures", 0)
        self.repo.set("auth_blocked_until", 0)

    def verify(self, password: str) -> bool:
        blocked = self.repo.get("auth_blocked_until", 0)
        if time.time() < blocked:
            raise ValueError(f"Too many attempts. Try again in {int(blocked - time.time()) + 1}s.")
        stored = self.repo.get("credential_hash")
        if not stored:
            return False
        try:
            valid = self.hasher.verify(stored, password)
        except (VerificationError, InvalidHashError):
            valid = False
        if valid:
            self.repo.set("auth_failures", 0)
            self.repo.set("auth_blocked_until", 0)
        else:
            failures = self.repo.get("auth_failures", 0) + 1
            self.repo.set("auth_failures", failures)
            if failures >= 5:
                self.repo.set("auth_blocked_until", time.time() + min(300, 30 * 2 ** min(failures - 5, 4)))
        return valid


class TemplateStore:
    def __init__(self, data: Path, backend=keyring):
        self.path = data / "face-template.enc"
        self.backend = backend
        self.account = str(data.resolve())

    @property
    def enrolled(self) -> bool:
        return self.path.is_file()

    def _cipher(self, create: bool = False) -> Fernet:
        key = self.backend.get_password("AURA AI biometrics", self.account)
        if not key and create:
            key = Fernet.generate_key().decode()
            self.backend.set_password("AURA AI biometrics", self.account, key)
        if not key:
            raise ValueError("Biometric encryption key is unavailable in the OS keychain.")
        return Fernet(key.encode())

    def save(self, embeddings: list[list[float]]) -> None:
        payload = self._cipher(True).encrypt(json.dumps(embeddings).encode())
        temporary = self.path.with_suffix(".tmp")
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as file:
            file.write(payload)
        temporary.replace(self.path)

    def load(self) -> list[list[float]]:
        return json.loads(self._cipher().decrypt(self.path.read_bytes()))

    def delete(self) -> None:
        if self.path.exists():
            self.path.unlink()
        try:
            self.backend.delete_password("AURA AI biometrics", self.account)
        except keyring.errors.PasswordDeleteError:
            pass


class MemoryKeyring:
    """In-process keyring for demos and tests — never use it for real biometric data."""

    def __init__(self):
        self._items: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, account: str):
        return self._items.get((service, account))

    def set_password(self, service: str, account: str, value: str) -> None:
        self._items[(service, account)] = value

    def delete_password(self, service: str, account: str) -> None:
        self._items.pop((service, account), None)
