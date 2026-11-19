import pytest

from aura.commands.platform_adapters import DryRunAdapter, PlatformAdapter
from aura.commands.validator import note_path, safe_url


@pytest.mark.parametrize("url", ["https://github.com", "https://www.google.com/search?q=x"])
def test_safe_url_accepts_allow_listed(url):
    assert safe_url(url) == url


@pytest.mark.parametrize("url", [
    "http://github.com", "https://evil.com", "https://user:pw@github.com", "https://github.com:8443",
    "javascript:alert(1)", "https://github.com/\\..", "file:///etc/passwd",
])
def test_safe_url_rejects(url):
    with pytest.raises(ValueError):
        safe_url(url)


@pytest.mark.parametrize("title", ["../etc/passwd", "a/b", "", ".hidden", "x" * 81])
def test_note_path_rejects_traversal(tmp_path, title):
    with pytest.raises(ValueError):
        note_path(tmp_path, title)


def test_note_path_rejects_symlink(tmp_path):
    (tmp_path / "link.txt").symlink_to(tmp_path / "elsewhere.txt")
    with pytest.raises(ValueError):
        note_path(tmp_path, "link")


def test_platform_adapter_never_uses_shell():
    calls = []
    adapter = PlatformAdapter(system="Darwin", runner=lambda args, **kw: calls.append((args, kw)))
    adapter.application("calculator")
    args, kwargs = calls[0]
    assert args == ["/usr/bin/open", "-a", "Calculator"] and kwargs["shell"] is False


def test_platform_adapter_rejects_unknown_app():
    with pytest.raises(ValueError):
        PlatformAdapter(system="Darwin", runner=lambda *a, **k: None).application("terminal")


def test_dry_run_adapter_validates_and_records():
    adapter = DryRunAdapter()
    adapter.website("https://github.com")
    adapter.application("editor")
    assert adapter.actions == [("website", "https://github.com"), ("application", "text editor")]
    with pytest.raises(ValueError):
        adapter.website("https://evil.com")
