"""The bundle service: the four operations every caller imports.

Each export format and the verifier live in their own module; this class is the seam
that binds them to a `Repository`. A bundle is `audit` profile — auditable, never
portable and never replayable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from evidrun.evidence.export.comparison_v1 import export_comparison
from evidrun.evidence.export.comparison_v2 import export_comparison_v2
from evidrun.evidence.export.run_v3 import export_run_v3
from evidrun.evidence.verify.dispatch import verify
from evidrun.infrastructure.database import Repository


class EvidenceBundleService:
    def __init__(self, repository: Repository):
        self.repository = repository

    def export_comparison(self, comparison_id: str, output_path: Path) -> Path:
        return export_comparison(self.repository, comparison_id, output_path)

    def export_comparison_v2(self, comparison_id: str, output_path: Path) -> Path:
        return export_comparison_v2(self.repository, comparison_id, output_path)

    def export_run_v3(self, run_id: str, output_path: Path) -> Path:
        return export_run_v3(self.repository, run_id, output_path)

    def verify(self, bundle_path: Path) -> dict[str, Any]:
        return verify(bundle_path)
