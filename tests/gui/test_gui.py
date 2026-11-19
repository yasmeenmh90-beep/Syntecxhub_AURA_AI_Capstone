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

    window.go(window.PAGE_HISTORY)
    assert window.history.table.rowCount() >= 2
    window.go(window.PAGE_SECURITY)
    assert not window.security.enroll_btn.isEnabled()  # models missing in sandbox

    page.submit("lock")
    qtbot.waitUntil(lambda: window.stack.currentIndex() == 0, timeout=3000)
    assert not window.s.session.authenticated


def test_demo_mode_flags_low_assurance(window):
    window.lock_screen.demo_btn.click()
    assert window.s.session.demo
    assert "not verified" in window.assistant_page.trust.text()
    window.go(window.PAGE_SECURITY)
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


def test_dashboard_reflects_activity(window, qtbot):
    window.lock_screen.demo_btn.click()
    assert window.pages.currentWidget() is window.dashboard      # lands on the dashboard
    assert window.toast.isVisible() and "Unlocked" in window.toast.text.text()
    bot = window.assistant
    for text in ("what time is it", "make me a sandwich", "tell me a joke"):
        bot.handle(text)
    window.go(window.PAGE_DASHBOARD)
    d = window.dashboard
    qtbot.waitUntil(lambda: d.t_commands.value.text() == "3", timeout=3000)   # count-up finished
    assert d.columns.data[-1][2] == 3 and d.columns.data[-1][0] == "Today"
    assert "2 of 3 succeeded" in d.outcome_value.text()
    assert {name for name, _ in d.intents.data} == {"get_time", "unknown_command", "chat_joke"}
    assert d.feed.count() > 2


def test_typing_indicator_shows_then_clears(window, qtbot):
    window.lock_screen.demo_btn.click()
    window.go(window.PAGE_ASSISTANT)
    page = window.assistant_page
    page.submit("what time is it")
    assert page.chat.typing is not None
    qtbot.waitUntil(lambda: page.chat.typing is None and not page.busy, timeout=3000)


def test_dashboard_refresh_leaves_no_orphan_labels(window, qtbot):
    from PySide6.QtWidgets import QLabel
    window.lock_screen.demo_btn.click()
    window.assistant.handle("what time is it")
    card = window.dashboard.feed.parentWidget()

    def visible_labels():
        return [w for w in card.findChildren(QLabel) if not w.isHidden()]
    window.go(window.PAGE_DASHBOARD)
    first = len(visible_labels())
    for _ in range(3):
        window.dashboard.refresh()
    assert len(visible_labels()) == first
