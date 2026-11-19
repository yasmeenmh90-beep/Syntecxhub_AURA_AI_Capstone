import pytest

pytest.importorskip("PySide6")

from aura.ui.main_window import MainWindow  # noqa: E402
from aura.ui.theme import STYLESHEET  # noqa: E402


@pytest.fixture
def window(qtbot, qapp, services):
    qapp.setStyleSheet(STYLESHEET)
    w = MainWindow(services)
    qtbot.addWidget(w)
    w.show()
    return w


def test_starts_locked_with_first_run_pin(window):
    assert window.stack.currentIndex() == 0
    assert window.lock_screen.pin_confirm.isVisibleTo(window.lock_screen)
    assert not window.lock_screen.face_btn.isEnabled()  # no models / enrollment in the sandbox


def test_pin_unlock_command_confirm_and_lock(window, qtbot, adapter):
    lock = window.lock_screen
    lock.pin.setText("capstone-pin")
    lock.pin_confirm.setText("mismatch-123")
    lock._pin_submit()
    assert "do not match" in lock.error.text()
    lock.pin_confirm.setText("capstone-pin")
    lock._pin_submit()
    assert window.stack.currentIndex() == 1 and window.s.session.authenticated

    page = window.assistant_page
    page.submit("Open GitHub")
    qtbot.waitUntil(lambda: bool(page.chat.cards), timeout=3000)
    page.chat.cards[-1].yes.click()
    qtbot.waitUntil(lambda: adapter.actions == [("website", "https://github.com")], timeout=3000)

    window.go(1)
    assert window.history.table.rowCount() >= 2
    window.go(2)
    assert not window.security.enroll_btn.isEnabled()  # models missing in sandbox

    page.submit("lock")
    qtbot.waitUntil(lambda: window.stack.currentIndex() == 0, timeout=3000)
    assert not window.s.session.authenticated


def test_demo_mode_flags_low_assurance(window):
    window.lock_screen.demo_btn.click()
    assert window.s.session.demo
    assert "not verified" in window.assistant_page.trust.text()
    window.go(2)
    assert not window.security.delete_btn.isEnabled()


def test_verified_pill_and_lock_shortcut(window, qtbot):
    from PySide6.QtCore import Qt
    lock = window.lock_screen
    lock.pin.setText("capstone-pin")
    lock.pin_confirm.setText("capstone-pin")
    lock._pin_submit()
    assert window.assistant_page.trust.text() == "✓ Verified session"
    window.activateWindow()
    window.setFocus()
    qtbot.keyClick(window, Qt.Key_L, Qt.ControlModifier)  # Qt's Ctrl is ⌘ on macOS
    qtbot.waitUntil(lambda: window.stack.currentIndex() == 0, timeout=2000)
    assert not window.s.session.authenticated
