from aura.dialog.intents import Intent


def run(services, name, confirmed=False, **params):
    return services.executor.execute(Intent(name, params), confirmed=confirmed)


def test_commands_refused_while_locked(services):
    result = run(services, "get_time")
    assert result.status == "error" and "Unlock" in result.message


def test_external_actions_need_confirmation(services, adapter):
    services.session.unlock("Local PIN / password")
    first = run(services, "open_website", website="github")
    assert first.status == "confirmation_required" and adapter.actions == []
    second = run(services, "open_website", confirmed=True, website="github")
    assert second.status == "success" and adapter.actions == [("website", "https://github.com")]


def test_notes_round_trip_and_privacy(services):
    services.session.unlock("Local PIN / password")
    assert run(services, "create_note", title="ideas", body="secret plan").status == "success"
    assert run(services, "read_note", confirmed=True, title="ideas").message == "secret plan"
    logged = " ".join(r["message"] for r in services.repository.history())
    assert "secret plan" not in logged  # Note bodies never reach the history table.


def test_overwriting_a_note_requires_confirmation(services):
    services.session.unlock("Local PIN / password")
    run(services, "create_note", title="ideas", body="v1")
    assert run(services, "create_note", title="ideas", body="v2").status == "confirmation_required"


def test_missing_note_has_friendly_error(services):
    services.session.unlock("Local PIN / password")
    result = run(services, "read_note", confirmed=True, title="nope")
    assert result.status == "error" and "No note called" in result.message


def test_note_size_limit(services):
    services.session.unlock("Local PIN / password")
    assert run(services, "create_note", title="big", body="x" * 1601).status == "error"


def test_unknown_is_rejected_and_logged(services):
    services.session.unlock("Local PIN / password")
    assert run(services, "unknown_command").status == "rejected"
    assert services.repository.history()[0]["intent"] == "unknown_command"
