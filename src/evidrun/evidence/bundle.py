"""The bundle service: the four operations every caller imports.

Each export format and the verifier live in their own module; this class is the seam
that binds them to a `Repository`. A bundle is `audit` profile — auditable, never
portable and never replayable.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from evidrun.evidence.export.comparison_v1 import export_comparison
from evidrun.evidence.export.comparison_v2 import export_comparison_v2
from evidrun.evidence.export.run_v3 import export_run_v3
from evidrun.evidence.export.run_v4 import export_run_v4
from evidrun.evidence.verify.dispatch import verify
from evidrun.infrastructure.database import Repository
from evidrun.security import emit_secure_log

logger = logging.getLogger(__name__)


class EvidenceBundleService:
    def __init__(self, repository: Repository):
        self.repository = repository

    def export_comparison(self, comparison_id: str, output_path: Path) -> Path:
        exported = export_comparison(self.repository, comparison_id, output_path)
        self._log_export(comparison_id, "comparison-v1")
        return exported

    def export_comparison_v2(self, comparison_id: str, output_path: Path) -> Path:
        exported = export_comparison_v2(self.repository, comparison_id, output_path)
        self._log_export(comparison_id, "comparison-v2")
        return exported

    def export_run_v3(self, run_id: str, output_path: Path) -> Path:
        exported = export_run_v3(self.repository, run_id, output_path)
        self._log_export(run_id, "run-v3", bundle_version="3")
        return exported

    def export_run_v4(self, run_id: str, output_path: Path) -> Path:
        exported = export_run_v4(self.repository, run_id, output_path)
        self._log_export(run_id, "run-v4", bundle_version="4")
        return exported

    def export_run(self, run_id: str, output_path: Path) -> tuple[Path, str]:
        """Dispatch only on recorded trust presence; never infer a trust kind."""

        record = self.repository.read_model.get_run_record(run_id)
        if record is None:
            raise ValueError("Run has no canonical RunRecord")
        if record.execution_trust is None:
            return self.export_run_v3(run_id, output_path), "3"
        return self.export_run_v4(run_id, output_path), "4"

    def verify(self, bundle_path: Path) -> dict[str, Any]:
        result = verify(bundle_path)
        emit_secure_log(
            logger,
            logging.INFO,
            "bundle.verify.completed",
            fields={"operation": "verify"},
        )
        return result

    @staticmethod
    def _log_export(
        correlation_id: str, operation: str, *, bundle_version: str | None = None
    ) -> None:
        fields: dict[str, object] = {"operation": operation}
        if bundle_version is not None:
            fields["bundle_version"] = bundle_version
        emit_secure_log(
            logger,
            logging.INFO,
            "bundle.export.completed",
            correlation_id=correlation_id,
            fields=fields,
        )
