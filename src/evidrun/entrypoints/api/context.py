"""What every route needs, passed explicitly instead of captured by closure.

`create_app` used to declare all 36 handlers inside one function so they could
close over these collaborators. The context makes that dependency a parameter, so
a router lives in its own file and states what it uses.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from evidrun.evidence.bundle import EvidenceBundleService
from evidrun.infrastructure.database import Repository
from evidrun.infrastructure.providers import ProviderCredentialStore
from evidrun.runs import EvidrunService
from evidrun.settings import Settings


@dataclass(frozen=True, slots=True)
class ApiContext:
    """The composed runtime one API process serves requests from."""

    settings: Settings
    repository: Repository
    service: EvidrunService
    bundles: EvidenceBundleService
    provider_credentials: ProviderCredentialStore
    benchmarks: Path
