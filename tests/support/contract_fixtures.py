"""Shared fixtures for the contract test suite.

Every helper here moved verbatim out of ``tests/unit/test_contracts.py`` when that module was
split by subject. They build the CRL-CTX-002 legacy package, an accepted registry and the
baseline RunSpecs that most contract tests start from.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from evidrun.contracts import (
    InputBinding,
    RepositoryFixtureDecisionAuthority,
    RevisionDecisionRecord,
    RevisionEnvelope,
    RunSpec,
)
from evidrun.contracts.compiler import StudyCompiler
from evidrun.contracts.legacy import ExperimentManifestV1Adapter, LegacyStudyPackage
from evidrun.contracts.registry import InMemoryContractRegistry
from evidrun.experiments import ExperimentManifest
from evidrun.shared.types import sha256_bytes, sha256_json, utc_now
from tests.support import admission_specs

declared_service = admission_specs.declared_admission_service
scripted_service = admission_specs.scripted_admission_service

ROOT = Path(__file__).resolve().parents[2]


def legacy_package() -> tuple[ExperimentManifest, LegacyStudyPackage]:
    manifest_path = ROOT / "benchmarks/experiments/crl-ctx-002-demo.yaml"
    fixture_path = ROOT / "benchmarks/scenarios/crl-ctx-002/fixtures/long.log"
    manifest = ExperimentManifest.model_validate(yaml.safe_load(manifest_path.read_text()))
    package = ExperimentManifestV1Adapter().convert(
        manifest,
        project_id="project-contract-tests",
        fixture_path=fixture_path,
    )
    return manifest, package


def accepted_registry(package: LegacyStudyPackage) -> InMemoryContractRegistry:
    revisions = package.revisions
    decisions = package.acceptance_decisions()
    registry = InMemoryContractRegistry(allow_repository_fixture=True)
    for revision in revisions:
        registry.add(revision)
    for decision in decisions:
        registry.decide(decision)
    return registry


def baseline_specs() -> tuple[
    ExperimentManifest,
    LegacyStudyPackage,
    InMemoryContractRegistry,
    tuple[RunSpec, ...],
]:
    manifest, package = legacy_package()
    registry = accepted_registry(package)
    specs = StudyCompiler(registry).compile(package.study)
    return manifest, package, registry, specs


def materialized_subject_inputs(spec: RunSpec) -> tuple[InputBinding, ...]:
    return tuple(
        item.model_copy(
            update={
                "source": item.source.model_copy(
                    update={
                        "artifact_id": f"context-snapshot:{item.id}",
                        "digest": sha256_bytes(f"materialized:{item.id}".encode()),
                    }
                )
            }
        )
        for item in spec.scenario.input_bindings
        if item.visibility in {"subject", "subject_and_evaluator"}
    )


def accept(registry: InMemoryContractRegistry, revision: RevisionEnvelope) -> None:
    registry.add(revision)
    registry.decide(
        RevisionDecisionRecord(
            revision_ref=revision.ref,
            decision="accepted",
            authority=RepositoryFixtureDecisionAuthority(
                fixture_digest=sha256_json(revision.ref.model_dump(mode="json")),
            ),
            rationale="Accepted by the contract test fixture.",
            decided_at_utc=utc_now(),
        )
    )
