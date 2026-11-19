import pytest

from aura.authentication.credentials import Credentials, MemoryKeyring, TemplateStore
from aura.database.repository import Repository


@pytest.fixture
def creds(tmp_path):
    return Credentials(Repository(tmp_path / "t.db"))


def test_setup_and_verify(creds):
    assert not creds.configured
    creds.setup("correct-horse")
    assert creds.configured and creds.verify("correct-horse") and not creds.verify("wrong-pass")


def test_hash_not_plaintext(creds):
    creds.setup("correct-horse")
    assert "correct-horse" not in creds.repo.get("credential_hash")


@pytest.mark.parametrize("weak", ["", "1234567", "x" * 257])
def test_length_policy(creds, weak):
    with pytest.raises(ValueError):
        creds.setup(weak)


def test_cannot_overwrite_existing_credential(creds):
    creds.setup("correct-horse")
    with pytest.raises(ValueError):
        creds.setup("another-one")


def test_lockout_after_five_failures(creds):
    creds.setup("correct-horse")
    for _ in range(5):
        assert not creds.verify("nope-nope")
    with pytest.raises(ValueError, match="Too many attempts"):
        creds.verify("correct-horse")


def test_template_store_encrypts(tmp_path):
    store = TemplateStore(tmp_path, MemoryKeyring())
    store.save([[0.5, 0.25]])
    assert store.enrolled and b"0.25" not in store.path.read_bytes()
    assert store.load() == [[0.5, 0.25]]
    assert oct(store.path.stat().st_mode & 0o777) == "0o600"
    store.delete()
    assert not store.enrolled


def test_template_unreadable_without_key(tmp_path):
    keyring = MemoryKeyring()
    store = TemplateStore(tmp_path, keyring)
    store.save([[1.0]])
    keyring._items.clear()
    with pytest.raises(ValueError, match="keychain"):
        store.load()
