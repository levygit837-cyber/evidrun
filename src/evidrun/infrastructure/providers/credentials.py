"""Provider credential lookup that cannot hang the process.

`keyring.get_password` is an FFI call into the OS credential backend. On macOS an
unsigned binary is an unknown requestor, so the Keychain blocks waiting for an
authorization that never arrives in a non-interactive process. The call neither
raises nor returns, so a `try/except` around it protects nothing.

An FFI call in progress cannot be interrupted, so the lookup runs on a thread the
caller can abandon. That thread is a raw `threading.Thread(daemon=True)` and not a
`ThreadPoolExecutor`: the executor registers an `atexit` hook that joins its workers,
so a worker stuck inside the backend would keep the interpreter alive at exit and
reproduce the very hang this module exists to prevent.

Reporting an unavailable credential is strictly better than a command that never
returns. Absence is only claimed when the backend actually answered.
"""

from __future__ import annotations

import os
import threading
from enum import StrEnum

import keyring

from evidrun.providers import ProviderProfile

__all__ = [
    "CredentialAvailability",
    "CredentialLookup",
    "MissingProviderCredentialError",
    "ProviderCredentialStore",
]

#: How long to wait for the OS credential backend before declaring it unavailable.
#: Generous for a local keychain round trip, short enough that no command looks stuck.
CREDENTIAL_LOOKUP_TIMEOUT_SECONDS = 5.0

#: Opt-out for an environment whose backend is legitimately slower.
TIMEOUT_ENVIRONMENT_VARIABLE = "EVIDRUN_CREDENTIAL_TIMEOUT_SECONDS"


class MissingProviderCredentialError(RuntimeError):
    pass


class CredentialAvailability(StrEnum):
    """Why a credential is or is not usable, as three distinguishable outcomes."""

    AVAILABLE = "available"
    #: The backend answered and holds no credential for this profile.
    ABSENT = "absent"
    #: The backend did not answer in time, or failed. Nothing is known either way.
    UNAVAILABLE = "unavailable"


class CredentialLookup:
    """The outcome of one lookup: never the secret, only whether it can be used."""

    __slots__ = ("availability", "source")

    def __init__(self, availability: CredentialAvailability, source: str | None) -> None:
        self.availability = availability
        self.source = source

    @property
    def available(self) -> bool:
        return self.availability is CredentialAvailability.AVAILABLE

    def document(self) -> dict[str, object]:
        """The public projection. Deliberately cannot carry the secret."""

        return {
            "credential_available": self.available,
            "credential_availability": self.availability.value,
            "credential_source": self.source,
        }


class _BackendProbe:
    """One in-flight backend call, resolvable or abandonable exactly once."""

    __slots__ = ("_answered", "_failed", "_secret")

    def __init__(self, service: str, username: str) -> None:
        self._answered = threading.Event()
        self._secret: str | None = None
        self._failed = False
        thread = threading.Thread(
            target=self._run,
            args=(service, username),
            name="evidrun-credential-probe",
            daemon=True,
        )
        thread.start()

    def _run(self, service: str, username: str) -> None:
        try:
            self._secret = keyring.get_password(service, username)
        except Exception:
            # The message is discarded on purpose: a backend error can quote the
            # requested account, and nothing here belongs in a log.
            self._failed = True
        finally:
            self._answered.set()

    def wait(self, timeout: float) -> tuple[CredentialAvailability, str | None]:
        if not self._answered.wait(timeout):
            return CredentialAvailability.UNAVAILABLE, None
        if self._failed:
            return CredentialAvailability.UNAVAILABLE, None
        if self._secret:
            return CredentialAvailability.AVAILABLE, self._secret
        return CredentialAvailability.ABSENT, None

    @property
    def settled(self) -> bool:
        return self._answered.is_set()


class ProviderCredentialStore:
    environment_variable = "EVIDRUN_PROVIDER_API_KEY"

    def __init__(self) -> None:
        self._probe: _BackendProbe | None = None

    def _timeout_seconds(self) -> float:
        raw = os.environ.get(TIMEOUT_ENVIRONMENT_VARIABLE)
        if not raw:
            return CREDENTIAL_LOOKUP_TIMEOUT_SECONDS
        try:
            parsed = float(raw)
        except ValueError:
            return CREDENTIAL_LOOKUP_TIMEOUT_SECONDS
        return parsed if parsed > 0 else CREDENTIAL_LOOKUP_TIMEOUT_SECONDS

    def _resolve(
        self, profile: ProviderProfile
    ) -> tuple[CredentialAvailability, str | None]:
        """Resolve against the backend without ever blocking indefinitely."""

        probe = self._probe
        if probe is None or probe.settled:
            # A probe still stuck in the backend is reused rather than replaced, so a
            # second call cannot queue another blocked thread behind the first.
            probe = _BackendProbe(profile.credential_service, profile.id)
            self._probe = probe
        return probe.wait(self._timeout_seconds())

    def lookup(self, profile: ProviderProfile) -> CredentialLookup:
        """Report availability, distinguishing absent from unavailable."""

        if os.environ.get(self.environment_variable):
            return CredentialLookup(CredentialAvailability.AVAILABLE, "environment")
        availability = self._resolve(profile)[0]
        source = "system_keychain" if availability is CredentialAvailability.AVAILABLE else None
        return CredentialLookup(availability, source)

    def get(self, profile: ProviderProfile) -> str | None:
        """Return the secret, or None when it is absent or the backend is unavailable."""

        environment_value = os.environ.get(self.environment_variable)
        if environment_value:
            return environment_value
        return self._resolve(profile)[1]

    def require(self, profile: ProviderProfile) -> str:
        environment_value = os.environ.get(self.environment_variable)
        if environment_value:
            return environment_value
        availability, secret = self._resolve(profile)
        if secret:
            return secret
        raise MissingProviderCredentialError(
            f"Credencial {availability.value} para {profile.id}; "
            "execute `evidrun provider set-key`."
        )

    def set(self, profile: ProviderProfile, api_key: str) -> None:
        value = api_key.strip()
        if not value:
            raise ValueError("API key cannot be empty")
        keyring.set_password(profile.credential_service, profile.id, value)
        self._probe = None

    def source(self, profile: ProviderProfile) -> str | None:
        return self.lookup(profile).source
