from __future__ import annotations

import os

import keyring

from evidrun.providers import ProviderProfile


class MissingProviderCredentialError(RuntimeError):
    pass


class ProviderCredentialStore:
    environment_variable = "EVIDRUN_PROVIDER_API_KEY"

    def get(self, profile: ProviderProfile) -> str | None:
        environment_value = os.environ.get(self.environment_variable)
        if environment_value:
            return environment_value
        return keyring.get_password(profile.credential_service, profile.id)

    def require(self, profile: ProviderProfile) -> str:
        value = self.get(profile)
        if not value:
            raise MissingProviderCredentialError(
                f"Credencial ausente para {profile.id}; execute `evidrun provider set-key`."
            )
        return value

    def set(self, profile: ProviderProfile, api_key: str) -> None:
        value = api_key.strip()
        if not value:
            raise ValueError("API key cannot be empty")
        keyring.set_password(profile.credential_service, profile.id, value)

    def source(self, profile: ProviderProfile) -> str | None:
        if os.environ.get(self.environment_variable):
            return "environment"
        return "system_keychain" if self.get(profile) else None
