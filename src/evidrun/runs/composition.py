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
    try:
        credential_available = credentials.get(profile) is not None
    except Exception:
        # A missing/unavailable OS credential backend must fail admission closed,
        # not prevent deterministic/offline workers from starting.
        credential_available = False
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
