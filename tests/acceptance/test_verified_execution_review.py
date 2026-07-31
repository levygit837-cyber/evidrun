from __future__ import annotations

import asyncio
import hashlib
import json
import zipfile
from pathlib import Path

import yaml
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from evidrun.contracts import capability_ref, semantic_model_dump
from evidrun.contracts.authoring.evaluation import (
    EvaluationDisclosure,
    EvaluationPlanRevision,
    SubjectEvaluationDisclosure,
)
from evidrun.contracts.authoring.inventory import (
    AgentInventoryRevision,
    CapabilityRequirement,
)
from evidrun.contracts.authoring.protocol import (
    AlwaysTrigger,
    InteractionEdge,
    InteractionNode,
    InteractionProtocolRevision,
    InteractionProtocolSpec,
)
from evidrun.contracts.authoring.scenario import ScenarioRevision
from evidrun.contracts.legacy import ExperimentManifestV1Adapter
from evidrun.entrypoints.api.app import create_app
from evidrun.entrypoints.cli.app import app as cli_app
from evidrun.entrypoints.review_html import render_review_package_html
from evidrun.evidence.bundle import EvidenceBundleService
from evidrun.experiments import ExperimentManifest
from evidrun.infrastructure.artifacts.store import ArtifactStore
from evidrun.infrastructure.database import Database, Repository
from evidrun.runs import DurableRunWorker, EvidrunService
from evidrun.settings import Settings
from evidrun.shared.types import Classification
from tests.support.human_attestation import (
    TestHumanAttestationVerifier,
    accepted_decision,
)
from tests.support.runtime_study import build_runtime_study

ROOT = Path(__file__).resolve().parents[2]


def _archive_files(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def _write_resealed(path: Path, files: dict[str, bytes]) -> None:
    checksums = {
        name: hashlib.sha256(content).hexdigest()
        for name, content in files.items()
        if name != "checksums.json"
    }
    files["checksums.json"] = (
        json.dumps(
            {
                "schema_version": "4",
                "created_at": "2026-07-30T00:00:00+00:00",
                "files": checksums,
            },
            sort_keys=True,
            indent=2,
        )
        + "\n"
    ).encode()
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)


def _repository(tmp_path: Path) -> tuple[Database, Repository]:
    database = Database(tmp_path / "evidrun.db")
    database.create_all()
    return database, Repository(database, TestHumanAttestationVerifier())


def _registered_study(repository: Repository, tmp_path: Path):
    workspace = repository.catalog.create_workspace("Verified lineage workspace")
    project = repository.catalog.create_project(workspace.id, "Verified lineage project")
    source = ArtifactStore(tmp_path / "artifacts").put_ref(
        b"ROOT_CAUSE=SEARCH_INDEX_LAG\n",
        project_id=project.id,
        media_type="text/plain",
        classification=Classification.INTERNAL,
    )
    revisions, study = build_runtime_study(project_id=project.id, source=source)
    study_id = ""
    for revision in revisions:
        row = repository.registry.save_contract_revision(revision, status="draft")
        if revision == study:
            study_id = row.id
    return revisions, study, study_id, source


def test_verified_promotion_creates_new_trust_admission_and_run(tmp_path: Path) -> None:
    database, repository = _repository(tmp_path)
    revisions, _, study_id, _ = _registered_study(repository, tmp_path)
    service = EvidrunService(repository)

    unverified = service.execution_preparation.prepare(study_id).run_specs[0]
    unverified_admission = service.admission_service.admit(
        unverified.spec, unverified.execution_trust
    )
    unverified_admission_row = repository.catalog.save_admission_record(
        unverified.row_id, unverified_admission
    )
    run_a, _ = service.runtime.coordinator.enqueue(
        run_spec_id=unverified.row_id,
        admission_id=unverified_admission_row.id,
        idempotency_key="promotion-unverified-run",
    )

    repository.registry.decide_contract_revision(accepted_decision(revisions[0]))
    partial = service.execution_preparation.prepare(study_id).run_specs[0]
    assert partial.execution_trust.kind == "unverified_revision_set"
    for revision in revisions[1:]:
        repository.registry.decide_contract_revision(accepted_decision(revision))

    verified = service.execution_preparation.prepare(study_id).run_specs[0]
    assert verified.spec.digest == unverified.spec.digest
    assert verified.execution_trust.kind == "verified_revision_set"
    assert tuple(
        binding.revision_ref for binding in verified.execution_trust.verified_decisions
    ) == verified.execution_trust.revision_refs
    assert verified.execution_trust.trust_id != unverified.execution_trust.trust_id

    verified_admission = service.admission_service.admit(
        verified.spec, verified.execution_trust
    )
    assert verified_admission.decision == "admitted"
    verified_admission_row = repository.catalog.save_admission_record(
        verified.row_id, verified_admission
    )
    run_b, verified_job = service.runtime.coordinator.enqueue(
        run_spec_id=verified.row_id,
        admission_id=verified_admission_row.id,
        idempotency_key="promotion-verified-run",
    )

    assert run_b != run_a
    assert verified_admission_row.id != unverified_admission_row.id
    record_a = repository.read_model.get_run_record(run_a)
    record_b = repository.read_model.get_run_record(run_b)
    assert record_a is not None and record_b is not None
    assert record_a.execution_trust == unverified.execution_trust.ref
    assert record_b.execution_trust == verified.execution_trust.ref
    dashboard = {
        item["id"]: item for item in repository.read_model.latest_dashboard()["runs"]
    }
    assert dashboard[run_a]["execution_trust"]["kind"] == "unverified_revision_set"
    assert dashboard[run_b]["execution_trust"]["kind"] == "verified_revision_set"
    assert dashboard[run_a]["isolation"] == "in_process"
    assert dashboard[run_b]["isolation"] == "in_process"
    assert repository.execution_trust.get_record(
        unverified.execution_trust.trust_id
    ).kind == "unverified_revision_set"

    worker = DurableRunWorker(
        repository,
        service.runtime.coordinator,
        worker_id="verified-promotion-worker",
    )
    assert asyncio.run(worker.process_once(job_id=verified_job.job_id)) is True
    assert repository.read_model.get_run(run_b).status == "completed"
    bundle_path = tmp_path / "verified-run-v4.evidrun.zip"
    bundles = EvidenceBundleService(repository)
    bundles.export_run_v4(run_b, bundle_path)
    verification = bundles.verify(bundle_path)
    assert verification["valid"] is True, verification
    assert verification["records"]["__revision_decision_bindings__"] is True
    with zipfile.ZipFile(bundle_path) as archive:
        names = set(archive.namelist())
        assert len(
            [name for name in names if name.startswith("revision-decisions/")]
        ) == len(revisions)
        summary = archive.read("summary.html").decode("utf-8")
    assert "Trust</dt><dd>Verificada" in summary
    assert "Isolamento</dt><dd>in_process" in summary
    assert verified.execution_trust.trust_id in summary

    omitted = tmp_path / "verified-decision-omitted.zip"
    omitted_files = _archive_files(bundle_path)
    decision_name = next(
        name for name in omitted_files if name.startswith("revision-decisions/")
    )
    omitted_files.pop(decision_name)
    _write_resealed(omitted, omitted_files)
    assert bundles.verify(omitted)["valid"] is False

    confused = tmp_path / "verified-decision-confused-authority.zip"
    confused_files = _archive_files(bundle_path)
    decision_document = json.loads(confused_files[decision_name])
    decision_document["authority"] = {
        "kind": "repository_fixture",
        "fixture_id": "experiment-manifest-v1:crl-ctx-002",
        "fixture_digest": "c" * 64,
    }
    confused_files[decision_name] = (
        json.dumps(decision_document, sort_keys=True, indent=2) + "\n"
    ).encode()
    _write_resealed(confused, confused_files)
    assert bundles.verify(confused)["valid"] is False

    false_sandbox = tmp_path / "verified-false-sandbox-label.zip"
    sandbox_files = _archive_files(bundle_path)
    sandbox_files["summary.html"] = sandbox_files["summary.html"].replace(
        b"in_process", b"sandboxed"
    )
    _write_resealed(false_sandbox, sandbox_files)
    assert bundles.verify(false_sandbox)["valid"] is False

    appended_sandbox = tmp_path / "verified-appended-sandbox-claim.zip"
    appended_files = _archive_files(bundle_path)
    appended_files["summary.html"] = appended_files["summary.html"].replace(
        b"</body>", b"<strong>sandboxed</strong></body>"
    )
    _write_resealed(appended_sandbox, appended_files)
    assert bundles.verify(appended_sandbox)["valid"] is False
    database.dispose()


def test_human_decisions_promote_a_nonhuman_repository_fixture(tmp_path: Path) -> None:
    database, repository = _repository(tmp_path)
    workspace = repository.catalog.create_workspace("Fixture promotion workspace")
    project = repository.catalog.create_project(workspace.id, "Fixture promotion project")
    manifest = ExperimentManifest.model_validate(
        yaml.safe_load(
            (ROOT / "benchmarks/experiments/crl-ctx-002-demo.yaml").read_text()
        )
    )
    fixture_path = ROOT / "benchmarks/scenarios/crl-ctx-002/fixtures/long.log"
    fixture_ref = ArtifactStore(tmp_path / "fixture-artifacts").put_ref(
        fixture_path.read_bytes(),
        project_id=project.id,
        media_type="text/plain",
        classification=Classification.INTERNAL,
    )
    package = ExperimentManifestV1Adapter().convert(
        manifest,
        project_id=project.id,
        fixture_ref=fixture_ref,
    )
    repository.registry.import_legacy_contract_package(package)
    study_row = next(
        row
        for row in repository.read_model.list_contract_revisions(project.id)
        if row["contract_type"] == "study"
    )
    service = EvidrunService(repository)
    before = service.execution_preparation.prepare(str(study_row["id"]))
    assert {
        item.execution_trust.kind for item in before.run_specs
    } == {"unverified_revision_set"}

    for revision in package.revisions:
        stored = repository.registry.decide_contract_revision(
            accepted_decision(revision)
        )
        assert stored.actor_type == "verified_human"
    after = service.execution_preparation.prepare(str(study_row["id"]))
    assert {
        item.execution_trust.kind for item in after.run_specs
    } == {"verified_revision_set"}
    assert {
        item.execution_trust.trust_id for item in before.run_specs
    }.isdisjoint(
        {item.execution_trust.trust_id for item in after.run_specs}
    )
    database.dispose()


def test_review_package_diff_uses_only_persisted_complete_targets(tmp_path: Path) -> None:
    database, repository = _repository(tmp_path)
    revisions, study, study_id, source = _registered_study(repository, tmp_path)
    service = EvidrunService(repository)
    first = service.execution_preparation.prepare(study_id)

    original_goal = revisions[0]
    original_scenario = next(
        revision for revision in revisions if isinstance(revision, ScenarioRevision)
    )
    original_agent = next(
        revision for revision in revisions if isinstance(revision, AgentInventoryRevision)
    )
    original_evaluation = next(
        revision for revision in revisions if isinstance(revision, EvaluationPlanRevision)
    )
    original_protocol = next(
        revision
        for revision in revisions
        if isinstance(revision, InteractionProtocolRevision)
    )
    goal_v2 = original_goal.model_copy(
        update={
            "revision": 2,
            "payload": original_goal.payload.model_copy(
                update={"instruction": "Diagnostique a causa exata sem inferências extras."}
            ),
        }
    )
    added_scenario = original_scenario.model_copy(
        update={
            "logical_id": "runtime-secondary-scenario",
            "revision": 1,
            "title": "Segundo incidente exato para diff",
        }
    )
    capability = CapabilityRequirement(
        kind="tool",
        capability_ref=capability_ref("evidrun.tool", "read-artifact-text-v1"),
        minimum_interface_version="1",
        requested_permissions=("read:subject_artifacts",),
        exposure="instructions_and_schema",
        instruction_refs=(source,),
        authority_constraints=("subject-envelope-only",),
    )
    agent_v2 = original_agent.model_copy(
        update={
            "revision": 2,
            "payload": original_agent.payload.model_copy(
                update={"capability_requirements": (capability,)}
            ),
        }
    )
    evaluation_v2 = original_evaluation.model_copy(
        update={
            "revision": 2,
            "payload": original_evaluation.payload.model_copy(
                update={
                    "disclosure": EvaluationDisclosure(
                        subject=SubjectEvaluationDisclosure(
                            mode="pre_run",
                            dimension_ids=("root-cause-grounded",),
                        ),
                        hidden_input_refs=(source,),
                    )
                }
            ),
        }
    )
    classified_node_ref = source.model_copy(
        update={"classification": Classification.SENSITIVE}
    )
    protocol_v2 = original_protocol.model_copy(
        update={
            "revision": 2,
            "payload": InteractionProtocolSpec(
                mode="graph",
                max_turns=1,
                nodes=(
                    InteractionNode(
                        id="reviewed-prompt",
                        kind="prompt",
                        content_ref=classified_node_ref,
                    ),
                    InteractionNode(id="terminal", kind="terminal"),
                ),
                edges=(
                    InteractionEdge(
                        source="reviewed-prompt",
                        target="terminal",
                        trigger=AlwaysTrigger(),
                    ),
                ),
            ),
        }
    )
    blueprint_v2 = study.payload.run_blueprint.model_copy(
        update={
            "agent_inventory_ref": agent_v2.ref,
            "evaluation_plan_ref": evaluation_v2.ref,
            "interaction_protocol_ref": protocol_v2.ref,
        }
    )
    study_v2 = study.model_copy(
        update={
            "revision": 2,
            "payload": study.payload.model_copy(
                update={
                    "goal_ref": goal_v2.ref,
                    "scenario_refs": (original_scenario.ref, added_scenario.ref),
                    "run_blueprint": blueprint_v2,
                    "repetitions": 2,
                    "limitations": ("Não generaliza para outro incidente.",),
                }
            ),
        }
    )
    for revision in (
        goal_v2,
        added_scenario,
        agent_v2,
        evaluation_v2,
        protocol_v2,
    ):
        repository.registry.save_contract_revision(revision, status="draft")
    study_v2_row = repository.registry.save_contract_revision(study_v2, status="draft")
    second = service.execution_preparation.prepare(study_v2_row.id)

    package = service.review_packages.build(
        second.review_target.review_target_digest,
        compare_to_digest=first.review_target.review_target_digest,
    )
    document = semantic_model_dump(package)
    assert "review_package_digest" not in document
    assert package.diff is not None
    assert {
        original_goal.logical_id,
        original_agent.logical_id,
        original_evaluation.logical_id,
        original_protocol.logical_id,
        study.logical_id,
    }.issubset(
        {item.logical_id for item in package.diff.revision_refs_changed}
    )
    assert {item.logical_id for item in package.diff.revision_refs_added} == {
        added_scenario.logical_id
    }
    assert package.diff.run_specs_changed
    assert package.diff.run_specs_added
    assert any(change.endswith(".goal") for change in package.diff.semantic_changes)
    assert any(
        change.endswith(".agent_inventory")
        for change in package.diff.semantic_changes
    )
    assert any(
        change.endswith(".evaluation_plan")
        for change in package.diff.semantic_changes
    )
    assert any(
        change.endswith(".interaction_protocol")
        for change in package.diff.semantic_changes
    )
    assert any(
        change.endswith(".limitations") for change in package.diff.semantic_changes
    )
    projected = package.run_specs[0]
    assert projected.subject_disclosure.mode == "pre_run"
    assert projected.capability_requirements == (capability,)
    assert projected.requested_permissions == ("read:subject_artifacts",)
    assert projected.classifications == (
        Classification.INTERNAL,
        Classification.SENSITIVE,
    )
    assert projected.network.mode == "disabled"
    assert projected.external_effects.mode == "denied"
    assert projected.hidden_input_refs == (source,)
    assert projected.limitations
    assert projected.isolation == "in_process"
    assert projected.known_admission_refusals
    printable = render_review_package_html(package)
    for expected_text in (
        "Closure exata",
        "Capabilities",
        "Permissions",
        "Classifications",
        "EvaluationPlan",
        "Hidden-input refs",
        "Limitações",
        "Recusas de admissão conhecidas",
        capability.capability_ref.name,
        "read:subject_artifacts",
        source.digest,
    ):
        assert expected_text in printable

    study_v3 = study_v2.model_copy(
        update={
            "revision": 3,
            "payload": study_v2.payload.model_copy(
                update={"scenario_refs": (added_scenario.ref,)}
            ),
        }
    )
    study_v3_row = repository.registry.save_contract_revision(study_v3, status="draft")
    third = service.execution_preparation.prepare(study_v3_row.id)
    removal = service.review_packages.build(
        third.review_target.review_target_digest,
        compare_to_digest=second.review_target.review_target_digest,
    )
    assert removal.diff is not None
    assert {item.logical_id for item in removal.diff.revision_refs_removed} == {
        original_scenario.logical_id
    }
    assert removal.diff.run_specs_removed
    assert any(
        change == f"closure.removed[scenario:{original_scenario.logical_id}]"
        for change in removal.diff.semantic_changes
    )

    try:
        service.review_packages.build(
            second.review_target.review_target_digest,
            compare_to_digest="f" * 64,
        )
    except KeyError:
        pass
    else:
        raise AssertionError("a future, unpersisted ReviewTarget was accepted")
    database.dispose()


def test_api_cli_and_html_expose_the_same_review_package(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    settings = Settings.load(data_dir)
    settings.ensure_directories()
    database = Database(settings.database_path)
    database.create_all()
    repository = Repository(database)
    _, _, study_id, _ = _registered_study(repository, settings.data_dir)
    preparation = EvidrunService(repository).execution_preparation.prepare(study_id)
    target_digest = preparation.review_target.review_target_digest
    expected = semantic_model_dump(
        EvidrunService(repository).review_packages.build(target_digest)
    )
    database.dispose()

    app = create_app(data_dir=data_dir)
    with TestClient(app) as client:
        response = client.get(f"/api/v1/review-targets/{target_digest}/package")
        assert response.status_code == 200, response.text
        assert response.json() == expected
        assert "review_package_digest" not in response.json()
        html = client.get(f"/api/v1/review-targets/{target_digest}/package.html")
        assert html.status_code == 200
        assert target_digest in html.text
        assert "Projeção de revisão, não autoridade humana" in html.text
        future = client.get(f"/api/v1/review-targets/{'f' * 64}/package")
        assert future.status_code == 404

    result = CliRunner().invoke(
        cli_app,
        [
            "study",
            "review-package",
            target_digest,
            "--data-dir",
            str(data_dir),
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == expected
    app.state.repository.database.dispose()
