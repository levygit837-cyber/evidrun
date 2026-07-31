"""Credential lookup: bounded, and honest about which of three outcomes happened.

The bug this pins is a hang, not an exception. `keyring.get_password` is an FFI call into
the OS credential backend, and an unsigned binary is an unknown requestor on macOS, so the
Keychain blocks waiting for an authorization no non-interactive process can supply. The call
neither raises nor returns, so a `try/except` protects nothing and `doctor` never finishes.
"""

from __future__ import annotations

import threading
import time

import pytest

import evidrun.infrastructure.providers.credentials as credentials_module
from evidrun.infrastructure.providers import (
    CredentialAvailability,
    MissingProviderCredentialError,
    ProviderCredentialStore,
)
from evidrun.providers import ProviderProfile


@pytest.fixture(autouse=True)
def _no_ambient_credential(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ProviderCredentialStore.environment_variable, raising=False)
    monkeypatch.delenv(credentials_module.TIMEOUT_ENVIRONMENT_VARIABLE, raising=False)


def _profile() -> ProviderProfile:
    return ProviderProfile.load_default()


def test_a_blocking_backend_reports_unavailable_instead_of_hanging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    released = threading.Event()

    def block_until_released(service: str, username: str) -> str | None:
        del service, username
        released.wait(30)  # stands in for a Keychain prompt nobody can answer
        return None

    monkeypatch.setattr(credentials_module.keyring, "get_password", block_until_released)
    monkeypatch.setenv(credentials_module.TIMEOUT_ENVIRONMENT_VARIABLE, "0.2")
    store = ProviderCredentialStore()

    started = time.monotonic()
    outcome = store.lookup(_profile())
    elapsed = time.monotonic() - started

    assert outcome.availability is CredentialAvailability.UNAVAILABLE
    assert outcome.available is False
    assert outcome.source is None
    # Bounded by the timeout, nowhere near the 30s the backend would have held.
    assert elapsed < 5
    released.set()


def test_a_blocked_lookup_does_not_queue_a_second_backend_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    released = threading.Event()
    calls: list[str] = []

    def block_until_released(service: str, username: str) -> str | None:
        del username
        calls.append(service)
        released.wait(30)
        return None

    monkeypatch.setattr(credentials_module.keyring, "get_password", block_until_released)
    monkeypatch.setenv(credentials_module.TIMEOUT_ENVIRONMENT_VARIABLE, "0.2")
    store = ProviderCredentialStore()
    profile = _profile()

    for _ in range(3):
        assert store.lookup(profile).availability is CredentialAvailability.UNAVAILABLE

    # Reusing the in-flight probe keeps one blocked thread instead of three.
    assert len(calls) == 1
    released.set()


def test_an_answering_backend_distinguishes_absent_from_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        credentials_module.keyring, "get_password", lambda _service, _user: None
    )
    absent = ProviderCredentialStore().lookup(_profile())
    assert absent.availability is CredentialAvailability.ABSENT
    assert absent.source is None

    monkeypatch.setattr(
        credentials_module.keyring, "get_password", lambda _service, _user: "stored-secret"
    )
    available = ProviderCredentialStore().lookup(_profile())
    assert available.availability is CredentialAvailability.AVAILABLE
    assert available.source == "system_keychain"
    assert ProviderCredentialStore().get(_profile()) == "stored-secret"


def test_a_raising_backend_is_unavailable_rather_than_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def explode(service: str, username: str) -> str | None:
        del service
        raise RuntimeError(f"backend refused for {username}")

    monkeypatch.setattr(credentials_module.keyring, "get_password", explode)

    # Absence is a fact only when the backend answered; a failure knows nothing either way.
    outcome = ProviderCredentialStore().lookup(_profile())
    assert outcome.availability is CredentialAvailability.UNAVAILABLE


def test_the_environment_variable_short_circuits_the_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def must_not_run(_service: str, _user: str) -> str | None:
        raise AssertionError("the OS backend must not be consulted")

    monkeypatch.setattr(credentials_module.keyring, "get_password", must_not_run)
    monkeypatch.setenv(ProviderCredentialStore.environment_variable, "ephemeral-secret")
    store = ProviderCredentialStore()

    outcome = store.lookup(_profile())
    assert outcome.availability is CredentialAvailability.AVAILABLE
    assert outcome.source == "environment"
    assert store.get(_profile()) == "ephemeral-secret"
    assert store.require(_profile()) == "ephemeral-secret"


def test_the_public_projection_never_carries_the_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        credentials_module.keyring, "get_password", lambda _service, _user: "top-secret"
    )
    document = ProviderCredentialStore().lookup(_profile()).document()

    assert document == {
        "credential_available": True,
        "credential_availability": "available",
        "credential_source": "system_keychain",
    }
    assert "top-secret" not in str(document)


def test_require_names_the_outcome_without_quoting_the_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def explode(_service: str, _user: str) -> str | None:
        raise RuntimeError("account=private-account-name secret=leaked")

    monkeypatch.setattr(credentials_module.keyring, "get_password", explode)

    with pytest.raises(MissingProviderCredentialError) as captured:
        ProviderCredentialStore().require(_profile())

    message = str(captured.value)
    assert "unavailable" in message
    assert "private-account-name" not in message
    assert "leaked" not in message


def test_an_unusable_timeout_setting_still_resolves_normally(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A malformed timeout must not disable the lookup, only fall back to the default."""

    monkeypatch.setattr(
        credentials_module.keyring, "get_password", lambda _service, _user: "secret"
    )
    for raw in ("not-a-number", "0", "-3", ""):
        monkeypatch.setenv(credentials_module.TIMEOUT_ENVIRONMENT_VARIABLE, raw)
        outcome = ProviderCredentialStore().lookup(_profile())
        assert outcome.availability is CredentialAvailability.AVAILABLE


def test_an_explicit_timeout_setting_is_honoured(monkeypatch: pytest.MonkeyPatch) -> None:
    released = threading.Event()

    def block_until_released(_service: str, _user: str) -> str | None:
        released.wait(30)
        return None

    monkeypatch.setattr(credentials_module.keyring, "get_password", block_until_released)
    monkeypatch.setenv(credentials_module.TIMEOUT_ENVIRONMENT_VARIABLE, "0.05")

    started = time.monotonic()
    assert (
        ProviderCredentialStore().lookup(_profile()).availability
        is CredentialAvailability.UNAVAILABLE
    )
    # A shorter configured timeout must actually shorten the wait.
    assert time.monotonic() - started < 2
    released.set()
