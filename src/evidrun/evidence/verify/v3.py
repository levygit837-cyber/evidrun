"""Bundle v3: single-Run structure, durable execution records and the file allowlist.

v3 reuses every v2 record check and adds what only a Run bundle can assert: the
SubjectEnvelope binding, capability offers matching the admission, the lease/attempt
chain, and an exact member allowlist. A bundle that merely checksums is not audited.

The order in which results are recorded is deliberate: a failure part-way through
leaves the earlier keys already decided, exactly as the pre-extraction verifier did.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from itertools import pairwise
from typing import Any, cast

from evidrun.contracts import (
    AdmissionRecord,
    ArtifactManifest,
    ArtifactManifestEntry,
    CheckpointRecord,
    ResolvedCapability,
    RunExecutionAttempt,
    RunExecutionJob,
    RunRecord,
    RunSpec,
    SubjectEnvelopeRecord,
    semantic_model_dump,
)
from evidrun.evidence import archive as ar
from evidrun.evidence.verify.records import run_members, strip
from evidrun.evidence.verify.v2 import verify_v2_records
from evidrun.shared.types import canonical_json

MATERIALIZATION_EVENTS = frozenset(
    {"context.composed", "capability.offered", "subject.invoked", "subject.responded"}
)


def verify_v3_structure(bundle_manifest: dict[str, Any], names: set[str]) -> bool:
    raw_run_ids = bundle_manifest.get("run_ids")
    if not isinstance(raw_run_ids, list):
        return False
    run_ids = cast("list[object]", raw_run_ids)
    if (
        bundle_manifest.get("kind") != "run"
        or bundle_manifest.get("profile") != "audit"
        or bundle_manifest.get("artifact_content") != "references_only"
        or bundle_manifest.get("portable") is not False
        or bundle_manifest.get("replayable") is not False
        or len(run_ids) != 1
        or not isinstance(run_ids[0], str)
        or "artifact-manifest.json" not in names
    ):
        return False
    run_id = run_ids[0]
    return (
        run_members(run_id).issubset(names)
        and any(name.startswith("execution/jobs/") for name in names)
        and any(name.startswith("execution/attempts/") for name in names)
    )


@dataclass(frozen=True, slots=True)
class RunCore:
    """The contracts and events of the single Run a v3 bundle carries."""

    run_id: str
    run_record: RunRecord
    spec: RunSpec
    spec_digest: str
    admission: AdmissionRecord
    admission_digest: str
    events: list[dict[str, Any]]

    @property
    def invocations(self) -> list[dict[str, Any]]:
        return [event for event in self.events if event["type"] == "subject.invoked"]

    @property
    def resolved_capabilities(self) -> tuple[ResolvedCapability, ...]:
        return tuple(
            item
            for item in self.admission.resolved_inventory.capabilities
            if item.status == "resolved"
        )


def verify_v3_records(
    archive: zipfile.ZipFile,
    names: set[str],
    *,
    allowed_extra_names: set[str] | None = None,
    manifest_specs: tuple[RunSpec, ...] | None = None,
) -> dict[str, bool]:
    results = verify_v2_records(archive, names)
    results.pop("comparison.json", None)
    results.pop("artifact-manifest.json", None)
    try:
        core = _load_core(archive)
        subject_record = _record_subject(archive, names, core, results)
        results["__runtime_admission_binding__"] = _admission_binding_valid(
            core, subject_record is not None
        )
        job_name, attempts_name = _record_execution(archive, names, core, results)
        results["artifact-manifest.json"] = _manifest_valid(
            archive,
            core,
            subject_record,
            manifest_specs=manifest_specs,
        )
        results["__exact_file_allowlist__"] = names == _expected_names(
            core, job_name, attempts_name, subject_record is not None
        ) | (allowed_extra_names or set())
    except AttributeError, IndexError, KeyError, TypeError, ValueError:
        results["__v3_records__"] = False
    else:
        results["__v3_records__"] = True
    return results


def _load_core(archive: zipfile.ZipFile) -> RunCore:
    bundle = ar.read_json(archive, "bundle.json")
    run_id = str(bundle["run_ids"][0])
    run_record = RunRecord.model_validate(ar.read_json(archive, f"runs/{run_id}.json"))
    spec_document = ar.read_json(archive, f"run-specs/{run_record.run_spec_id}.json")
    spec_digest = spec_document.pop("digest")
    admission_document = ar.read_json(archive, f"admissions/{run_record.admission_id}.json")
    admission_digest = admission_document.pop("digest")
    return RunCore(
        run_id=run_id,
        run_record=run_record,
        spec=RunSpec.model_validate(spec_document),
        spec_digest=spec_digest,
        admission=AdmissionRecord.model_validate(admission_document),
        admission_digest=admission_digest,
        events=ar.read_events(archive, f"events/{run_id}.jsonl"),
    )


def _record_subject(
    archive: zipfile.ZipFile,
    names: set[str],
    core: RunCore,
    results: dict[str, bool],
) -> SubjectEnvelopeRecord | None:
    """A present envelope is validated against the spec; an absent one demands that
    nothing was ever materialized for the Subject."""

    subject_name = f"subject-envelopes/{core.run_id}.json"
    if subject_name not in names:
        results["__subject_envelope_absence__"] = not any(
            event["type"] in MATERIALIZATION_EVENTS for event in core.events
        )
        return None
    envelope_document = ar.read_json(archive, subject_name)
    envelope_digest = envelope_document.pop("digest")
    record = SubjectEnvelopeRecord.model_validate(envelope_document)
    results[subject_name] = (
        record.run_id == core.run_id
        and record.digest == envelope_digest
        and record.envelope.run_spec_digest == core.spec.digest == core.spec_digest
        and core.admission.digest == core.admission_digest
        and record.envelope.effective_capabilities == core.resolved_capabilities
        and _envelope_inputs_valid(record, core.spec)
        and len(core.invocations) <= 1
        and all(
            event["payload"]["subject_envelope_digest"] == record.digest
            for event in core.invocations
        )
    )
    return record


def _envelope_inputs_valid(record: SubjectEnvelopeRecord, spec: RunSpec) -> bool:
    """The envelope is a closed allowlist: exactly the bindings visible to the Subject."""

    visible_by_id = {
        item.id: item
        for item in spec.scenario.input_bindings
        if item.visibility in {"subject", "subject_and_evaluator"}
    }
    return set(visible_by_id) == {item.id for item in record.envelope.inputs} and all(
        item.role == visible_by_id[item.id].role
        and item.visibility == visible_by_id[item.id].visibility
        and item.mount_name == visible_by_id[item.id].mount_name
        and item.mount_access == visible_by_id[item.id].mount_access
        and item.source.media_type == visible_by_id[item.id].source.media_type
        and item.source.classification == visible_by_id[item.id].source.classification
        for item in record.envelope.inputs
    )


def _admission_binding_valid(core: RunCore, has_subject: bool) -> bool:
    """A capability offered to the Subject must be exactly the one admission resolved,
    and the invocation must reflect the admitted runner and provider."""

    expected_offers = {
        canonical_json(
            {
                "capability_ref": semantic_model_dump(item.resolved_ref),
                "required": item.required,
                "exposure": item.exposure,
                "effective_permissions": list(item.effective_permissions),
            }
        )
        for item in core.resolved_capabilities
        if item.resolved_ref is not None
    }
    actual_documents = [
        event["payload"] for event in core.events if event["type"] == "capability.offered"
    ]
    actual_offers = {canonical_json(item) for item in actual_documents}
    offers_valid = len(actual_documents) == len(actual_offers) and actual_offers == (
        expected_offers if has_subject else set()
    )
    inventory = core.admission.resolved_inventory
    expected_invocation = {
        "runner": inventory.runner_ref.name,
        "network": core.spec.workspace.network_policy.mode,
        "provider_profile_id": inventory.provider_profile_id,
        "provider_model": inventory.provider_model,
        "provider_reasoning_effort": inventory.provider_reasoning_effort,
        "provider_adapter": inventory.provider_adapter,
    }
    invocations_valid = len(core.invocations) <= 1 and all(
        all(event["payload"].get(key) == value for key, value in expected_invocation.items())
        for event in core.invocations
    )
    return offers_valid and invocations_valid


def _record_execution(
    archive: zipfile.ZipFile,
    names: set[str],
    core: RunCore,
    results: dict[str, bool],
) -> tuple[str, str]:
    job_names = sorted(name for name in names if name.startswith("execution/jobs/"))
    if len(job_names) != 1:
        raise ValueError("Bundle v3 requires exactly one execution job")
    job_document = ar.read_json(archive, job_names[0])
    job_digest = job_document.pop("digest")
    job = RunExecutionJob.model_validate(job_document)
    attempts_name = f"execution/attempts/{job.job_id}.json"
    attempts, digests_valid = _load_attempts(archive, attempts_name)
    results[job_names[0]] = (
        job.digest == job_digest
        and job.run_id == core.run_id
        and job.status in {"completed", "rejected"}
        and job.active_attempt_id is None
        and job.created_at_utc <= attempts[0].leased_at_utc
        and job.finished_at_utc is not None
        and attempts[-1].finished_at_utc is not None
        and job.finished_at_utc == attempts[-1].finished_at_utc
    )
    results[attempts_name] = digests_valid and _attempt_chain_valid(job, attempts)
    return job_names[0], attempts_name


def _load_attempts(
    archive: zipfile.ZipFile, attempts_name: str
) -> tuple[list[RunExecutionAttempt], bool]:
    attempts: list[RunExecutionAttempt] = []
    digests_valid = True
    for document in ar.read_json(archive, attempts_name):
        expected = document.pop("digest")
        attempt = RunExecutionAttempt.model_validate(document)
        attempts.append(attempt)
        digests_valid = digests_valid and attempt.digest == expected
    return attempts, digests_valid


def _attempt_chain_valid(job: RunExecutionJob, attempts: list[RunExecutionAttempt]) -> bool:
    """The lease chain is dense and ordered: one attempt per generation, each finished,
    and only the last shares the job's terminal status."""

    if not attempts:
        return False
    ordinals_dense = all(
        attempt.job_id == job.job_id
        and attempt.ordinal == index
        and attempt.lease_generation == index
        for index, attempt in enumerate(attempts, start=1)
    )
    unique = len({attempt.ordinal for attempt in attempts}) == len(attempts) and len(
        {attempt.lease_generation for attempt in attempts}
    ) == len(attempts)
    terminal_agrees = (
        job.lease_generation == attempts[-1].lease_generation
        and all(attempt.status in {"released", "expired"} for attempt in attempts[:-1])
        and (
            (job.status == "completed" and attempts[-1].status == "completed")
            or (job.status == "rejected" and attempts[-1].status == "rejected")
        )
    )
    timestamps_sane = all(
        attempt.last_heartbeat_at_utc < attempt.lease_expires_at_utc
        and attempt.finished_at_utc is not None
        and attempt.finished_at_utc >= attempt.leased_at_utc
        and attempt.last_heartbeat_at_utc <= attempt.finished_at_utc
        and (
            attempt.status != "expired"
            or attempt.finished_at_utc >= attempt.lease_expires_at_utc
        )
        for attempt in attempts
    )
    monotonic = all(
        earlier.leased_at_utc <= later.leased_at_utc for earlier, later in pairwise(attempts)
    )
    return ordinals_dense and unique and terminal_agrees and timestamps_sane and monotonic


def _manifest_valid(
    archive: zipfile.ZipFile,
    core: RunCore,
    subject_record: SubjectEnvelopeRecord | None,
    *,
    manifest_specs: tuple[RunSpec, ...] | None = None,
) -> bool:
    manifest_document = ar.read_json(archive, "artifact-manifest.json")
    manifest_digest = manifest_document.pop("digest")
    manifest = ArtifactManifest.model_validate(manifest_document)
    expected = _expected_entries(
        archive,
        core,
        subject_record,
        manifest_specs=manifest_specs,
    )
    canonical_expected = ar.artifact_manifest(expected).entries
    expected_set = {
        canonical_json(semantic_model_dump(item)) for item in canonical_expected
    }
    actual_set = {canonical_json(semantic_model_dump(item)) for item in manifest.entries}
    return (
        manifest.digest == manifest_digest
        and expected_set == actual_set
        and not manifest.portable
        and not manifest.replayable
    )


def _expected_entries(
    archive: zipfile.ZipFile,
    core: RunCore,
    subject_record: SubjectEnvelopeRecord | None,
    *,
    manifest_specs: tuple[RunSpec, ...] | None = None,
) -> list[ArtifactManifestEntry]:
    entries = [
        entry
        for spec in manifest_specs or (core.spec,)
        for entry in ar.spec_artifact_entries(core.run_id, spec)
    ]
    if subject_record is not None:
        entries.extend(ar.subject_artifact_entries(subject_record))
    entries.extend(ar.event_artifact_entries(core.run_id, core.events))
    entries.extend(
        ar.checkpoint_artifact_entries(
            core.run_id,
            [
                CheckpointRecord.model_validate(strip(document, "checkpoint_hash"))
                for document in ar.read_json(archive, f"checkpoints/{core.run_id}.json")
            ],
        )
    )
    return entries


def _expected_names(
    core: RunCore, job_name: str, attempts_name: str, has_subject: bool
) -> set[str]:
    """Exact allowlist: one member too many or too few invalidates the bundle."""

    names = {
        "bundle.json",
        "checksums.json",
        "artifact-manifest.json",
        f"run-specs/{core.run_record.run_spec_id}.json",
        f"admissions/{core.run_record.admission_id}.json",
        f"runs/{core.run_id}.json",
        f"events/{core.run_id}.jsonl",
        f"evaluations/{core.run_id}.json",
        f"checkpoints/{core.run_id}.json",
        job_name,
        attempts_name,
        *(ar.contract_member_name(item) for item in ar.spec_revision_refs(core.spec)),
    }
    if has_subject:
        names.add(f"subject-envelopes/{core.run_id}.json")
    return names
