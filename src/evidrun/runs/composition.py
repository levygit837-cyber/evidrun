from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from evidrun.infrastructure.artifacts.store import ArtifactStore
from evidrun.infrastructure.database import Repository
from evidrun.infrastructure.providers import (
    OpenAIResponsesProvider,
    ProviderCredentialStore,
)
from evidrun.providers import ProviderProfile
from evidrun.runs.adapters import (
    ArtifactInputMaterializer,
    ResponsesReadAgentAdapter,
    RuntimeAdapterCatalog,
)
from evidrun.runs.coordinator import RunExecutionCoordinator


@dataclass(frozen=True)
class RuntimeKernel:
    artifact_store: ArtifactStore
    catalog: RuntimeAdapterCatalog
    coordinator: RunExecutionCoordinator


def build_runtime_kernel(repository: Repository, artifacts_dir: Path) -> RuntimeKernel:
    artifact_store = ArtifactStore(artifacts_dir)
    profile = ProviderProfile.load_default()
    credentials = ProviderCredentialStore()
    # A bounded lookup already answers `unavailable` instead of hanging or raising, so an
    # offline worker starts while admission still fails closed on a missing credential.
    credential_available = credentials.lookup(profile).available
    real_subject = ResponsesReadAgentAdapter(
        OpenAIResponsesProvider(profile, credentials),
        profile,
        credential_available=credential_available,
    )
    catalog = RuntimeAdapterCatalog(
        real_subject=real_subject,
        materializer=ArtifactInputMaterializer(artifact_store)
    )
    coordinator = RunExecutionCoordinator(repository, artifact_store, catalog)
    return RuntimeKernel(
        artifact_store=artifact_store,
        catalog=catalog,
        coordinator=coordinator,
    )
