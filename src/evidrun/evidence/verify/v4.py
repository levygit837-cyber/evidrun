"""Bundle v4 trust validation layered over every Bundle v3 record check."""

from __future__ import annotations

import zipfile
from typing import Any, cast

from evidrun.contracts import (
    AdmissionRecord,
    ExecutionTrustRecord,
    RunRecord,
    RunSpec,
    parse_revision,
    validate_execution_trust_lineage,
)
from evidrun.evidence import archive as ar
from evidrun.evidence.verify.v3 import verify_v3_records, verify_v3_structure


def verify_v4_structure(bundle_manifest: dict[str, Any], names: set[str]) -> bool:
    trust = bundle_manifest.get("execution_trust")
    isolation = bundle_manifest.get("isolation")
    if not isinstance(trust, dict) or not isinstance(isolation, dict):
        return False
    trust_document = cast(dict[str, object], trust)
    isolation_document = cast(dict[str, object], isolation)
    trust_id = trust_document.get("trust_id")
    return (
        bundle_manifest.get("schema_version") == "4"
        and verify_v3_structure(bundle_manifest, names)
        and trust_document.get("kind")
        in {"unverified_revision_set", "verified_revision_set"}
        and isinstance(trust_id, str)
        and isinstance(trust_document.get("digest"), str)
        and isinstance(isolation_document.get("kind"), str)
        and f"execution-trust/{trust_id}.json" in names
    )


def verify_v4_records(archive: zipfile.ZipFile, names: set[str]) -> dict[str, bool]:
    results: dict[str, bool] = {}
    try:
        bundle = cast(dict[str, Any], ar.read_json(archive, "bundle.json"))
        trust_meta = cast(dict[str, Any], bundle["execution_trust"])
        trust_id = str(trust_meta["trust_id"])
        trust_name = f"execution-trust/{trust_id}.json"
        trust_document = cast(dict[str, Any], ar.read_json(archive, trust_name))
        stated_trust_digest = str(trust_document.pop("digest"))
        trust = ExecutionTrustRecord.model_validate(trust_document)

        run_id = str(cast(list[object], bundle["run_ids"])[0])
        run_record = RunRecord.model_validate(
            ar.read_json(archive, f"runs/{run_id}.json")
        )
        spec_document = cast(
            dict[str, Any],
            ar.read_json(archive, f"run-specs/{run_record.run_spec_id}.json"),
        )
        stated_spec_digest = str(spec_document.pop("digest"))
        spec = RunSpec.model_validate(spec_document)
        admission_document = cast(
            dict[str, Any],
            ar.read_json(
                archive, f"admissions/{run_record.admission_id}.json"
            ),
        )
        admission_document.pop("digest")
        admission = AdmissionRecord.model_validate(admission_document)

        revisions = tuple(
            _load_revision(archive, reference) for reference in trust.revision_refs
        )
        trust_contract_names = {
            ar.contract_member_name(reference) for reference in trust.revision_refs
        }
        actual_contract_names = {
            name for name in names if name.startswith("contracts/")
        }
        extra_contract_names = trust_contract_names - {
            ar.contract_member_name(reference)
            for reference in ar.spec_revision_refs(spec)
        }
        allowed_extras = {trust_name, *extra_contract_names}
        compiled_specs = validate_execution_trust_lineage(trust, spec, revisions)
        results.update(
            verify_v3_records(
                archive,
                names,
                allowed_extra_names=allowed_extras,
                manifest_specs=compiled_specs,
            )
        )
        results[trust_name] = (
            trust.trust_id == trust_id
            and trust.digest == stated_trust_digest == trust_meta.get("digest")
            and trust.kind == trust_meta.get("kind") == "unverified_revision_set"
            and not trust.verified_decisions
            and trust.run_spec_digest == spec.digest == stated_spec_digest
            and admission.execution_trust == trust.ref
            and run_record.execution_trust == trust.ref
            and run_record.run_id == run_id
            and bundle["isolation"]["kind"] == spec.workspace.runtime_kind
            and actual_contract_names == trust_contract_names
        )
        results["__execution_trust_lineage__"] = True
        results["__revision_decisions_absent__"] = not any(
            name.startswith("revision-decisions/") for name in names
        )
    except AttributeError, IndexError, KeyError, TypeError, ValueError:
        results["__v4_records__"] = False
    else:
        results["__v4_records__"] = True
    return results


def _load_revision(archive: zipfile.ZipFile, reference: Any) -> Any:
    document = cast(
        dict[str, Any], ar.read_json(archive, ar.contract_member_name(reference))
    )
    stated_digest = document.pop("digest")
    revision = parse_revision(document)
    if revision.ref != reference or revision.digest != stated_digest:
        raise ValueError("bundled contract revision digest mismatch")
    return revision
