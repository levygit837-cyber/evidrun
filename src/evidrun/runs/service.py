from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import yaml

from evidrun.contexts import ContextComposer
from evidrun.contracts import RunSpec
from evidrun.contracts.compiler import StudyCompiler
from evidrun.contracts.legacy import ExperimentManifestV1Adapter
from evidrun.experiments import ExperimentManifest
from evidrun.infrastructure.database import Repository
from evidrun.runs.composition import RuntimeKernel, build_runtime_kernel
from evidrun.runs.worker import DurableRunWorker
from evidrun.shared.types import Classification, new_id


class EvidrunService:
    """Compatibility facade; all Run execution is delegated to the Runtime Kernel."""

    def __init__(
        self, repository: Repository, *, runtime: RuntimeKernel | None = None
    ) -> None:
        self.repository = repository
        artifacts_dir = repository.database.path.parent / "artifacts"
        self.runtime = runtime or build_runtime_kernel(repository, artifacts_dir)
        self.composer = ContextComposer()
        self.runner = self.runtime.catalog.subject.runner
        self.admission_service = self.runtime.coordinator.admission_service

    def bootstrap_demo(self, benchmark_root: Path) -> dict[str, Any]:
        manifest_path = benchmark_root / "experiments" / "crl-ctx-002-demo.yaml"
        fixture_path = (
            benchmark_root / "scenarios" / "crl-ctx-002" / "fixtures" / "long.log"
        )
        manifest = ExperimentManifest.model_validate(
            yaml.safe_load(manifest_path.read_text())
        )

        dashboard = self.repository.read_model.latest_dashboard()
        if dashboard["workspaces"]:
            workspace_id = dashboard["workspaces"][0]["id"]
        else:
            workspace_id = self.repository.catalog.create_workspace("Laboratório local").id
        project = next(
            (p for p in dashboard["projects"] if p["name"] == "Context Reliability Lab"),
            None,
        )
        project_id = (
            project["id"]
            if project
            else self.repository.catalog.create_project(
                workspace_id, "Context Reliability Lab"
            ).id
        )
        revision = self.repository.catalog.save_experiment_revision(
            project_id=project_id, manifest=manifest.model_dump(mode="json")
        )
        fixture_ref = self.runtime.artifact_store.put_ref(
            fixture_path.read_bytes(),
            project_id=project_id,
            media_type="text/plain",
            classification=Classification.INTERNAL,
        )
        package = ExperimentManifestV1Adapter().convert(
            manifest,
            project_id=project_id,
            fixture_ref=fixture_ref,
        )
        self.repository.registry.import_legacy_contract_package(package)
        registry = self.repository.registry.contract_registry(project_id)
        run_specs = StudyCompiler(registry).compile(package.study)

        runs: dict[str, dict[str, Any]] = {}
        snapshots: dict[str, dict[str, Any]] = {}
        for spec in run_specs:
            run, snapshot, grade = asyncio.run(
                self._execute_spec(revision.id, spec, fixture_path.read_text())
            )
            runs[spec.variant_id] = {"run": run, "grade": grade}
            snapshots[spec.variant_id] = snapshot

        baseline = runs[manifest.baseline_variant]
        candidate_variant = next(
            variant.id
            for variant in manifest.variants
            if variant.id != manifest.baseline_variant
        )
        candidate = runs[candidate_variant]
        baseline_score = float(baseline["grade"]["score"])
        candidate_score = float(candidate["grade"]["score"])
        diff = self.composer.diff(
            snapshots[manifest.baseline_variant], snapshots[candidate_variant]
        )
        report = self._build_report(
            manifest=manifest,
            baseline_run=baseline["run"],
            candidate_run=candidate["run"],
            baseline_score=baseline_score,
            candidate_score=candidate_score,
            context_diff=diff,
        )
        comparison = self.repository.catalog.save_comparison(
            experiment_revision_id=revision.id,
            baseline_run_id=baseline["run"]["id"],
            candidate_run_id=candidate["run"]["id"],
            primary_variable=manifest.primary_variable,
            validity=manifest.validity,
            baseline_score=baseline_score,
            candidate_score=candidate_score,
            report_markdown=report,
        )
        return {
            "experiment_revision_id": revision.id,
            "study_revision": package.study.ref.model_dump(mode="json"),
            "comparison_id": comparison.id,
            "baseline_run_id": baseline["run"]["id"],
            "candidate_run_id": candidate["run"]["id"],
            "validity": manifest.validity,
            "context_diff": diff,
        }

    async def _execute_spec(
        self,
        experiment_revision_id: str,
        spec: RunSpec,
        source: str,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        del source
        spec_row = self.repository.catalog.save_run_spec(spec)
        admission = self.admission_service.admit(spec)
        admission_row = self.repository.catalog.save_admission_record(spec_row.id, admission)
        if admission.decision != "admitted":
            reasons = admission.missing_requirements or admission.denied_policies
            raise ValueError("deterministic RunSpec was rejected: " + ", ".join(reasons))
        run_id, job = self.runtime.coordinator.enqueue(
            run_spec_id=spec_row.id,
            admission_id=admission_row.id,
            idempotency_key=(
                f"demo:{experiment_revision_id}:{spec.digest}:{new_id('request')}"
            ),
            experiment_revision_id=experiment_revision_id,
        )
        worker = DurableRunWorker(
            self.repository,
            self.runtime.coordinator,
            worker_id=f"demo-worker:{run_id}",
        )
        await worker.process_once(job_id=job.job_id)
        run = self.repository.read_model.get_run(run_id)
        if run.status not in {"completed", "failed", "budget_exhausted"}:
            raise RuntimeError(f"demo Runtime Kernel stopped with Run status {run.status}")
        if run.status != "completed":
            last = self.repository.read_model.get_run_events(run_id)[-1]
            if last["type"] == "run.budget_exhausted":
                raise TimeoutError(str(last["payload"]["terminal_cause"]))
            raise RuntimeError(str(last["payload"]["terminal_cause"]))
        dashboard_runs = self.repository.read_model.latest_dashboard()["runs"]
        dashboard_run = next(item for item in dashboard_runs if item["id"] == run_id)
        envelope = self.repository.read_model.get_subject_envelope(run_id).envelope
        selected_content = self.runtime.artifact_store.get_verified(
            envelope.inputs[0].source
        ).decode("utf-8")
        snapshot = {
            **dashboard_run["context_snapshot"],
            "selected_content": selected_content,
        }
        grade_row = self.repository.read_model.get_grade(run_id)
        grade = {
            "score": grade_row.score,
            "passed": grade_row.passed,
            "rationale": grade_row.rationale,
            "evidence": json.loads(grade_row.evidence_json),
        }
        return {"id": run_id, "variant_id": spec.variant_id}, snapshot, grade

    @staticmethod
    def _build_report(
        *,
        manifest: ExperimentManifest,
        baseline_run: dict[str, Any],
        candidate_run: dict[str, Any],
        baseline_score: float,
        candidate_score: float,
        context_diff: dict[str, Any],
    ) -> str:
        return f"""# Relatório — {manifest.title}

## Resultado

- Variável primária: `{manifest.primary_variable}`
- Validade: `{manifest.validity}`
- Baseline: `{baseline_score:.2f}`
- Candidate: `{candidate_score:.2f}`
- Delta: `{candidate_score - baseline_score:+.2f}`

## Mudança observada

```json
{json.dumps(context_diff, ensure_ascii=False, indent=2)}
```

## Evidências

- Baseline run: `{baseline_run['id']}`
- Candidate run: `{candidate_run['id']}`

## Limitação

Este experimento usa um runner determinístico para verificar a infraestrutura do Evidrun. O
resultado não demonstra capacidade, estabilidade ou melhoria de um modelo de linguagem.
"""
