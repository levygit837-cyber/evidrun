from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from pydantic import ValidationError

from evidrun.contracts.authoring.study import StudySpec


def contract_ref(contract_type: str, logical_id: str) -> dict[str, object]:
    return {
        "contract_type": contract_type,
        "logical_id": logical_id,
        "revision": 1,
        "digest": "0" * 64,
    }


def valid_study() -> dict[str, Any]:
    return {
        "intent": {"purpose": "Comparar duas políticas de contexto."},
        "evidence_mode": "prospective_controlled",
        "goal_ref": contract_ref("goal", "goal"),
        "scenario_refs": [contract_ref("scenario", "scenario")],
        "run_blueprint": {
            "agent_inventory_ref": contract_ref("agent_inventory", "agent"),
            "workspace_template_ref": contract_ref("workspace_template", "workspace"),
            "interaction_protocol_ref": contract_ref("interaction_protocol", "interaction"),
            "evaluation_plan_ref": contract_ref("evaluation_plan", "evaluation"),
            "budgets": {"max_wall_seconds": 1},
            "stop_conditions": [{"kind": "goal_complete"}],
            "capture_policy": {"default_mode": "metadata"},
        },
        "variants": [
            {"id": "baseline", "label": "Baseline"},
            {"id": "candidate", "label": "Candidate"},
        ],
        "comparisons": [
            {
                "baseline_variant": "baseline",
                "candidate_variant": "candidate",
                "primary_variable": "context_policy",
            }
        ],
    }


def rejects(document: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        StudySpec.model_validate(document)


def test_minimal_existing_study_shape_remains_valid() -> None:
    study = StudySpec.model_validate(valid_study())

    assert study.intent.purpose
    assert study.scenario_refs
    assert study.variants


def test_intent_rejects_runtime_boundary_included_and_excluded_at_once() -> None:
    document = valid_study()
    document["intent"]["scope"] = {"included": ["runtime"], "excluded": ["runtime"]}

    rejects(document)


def test_intent_rejects_a_blank_purpose() -> None:
    document = valid_study()
    document["intent"]["purpose"] = "   "

    rejects(document)


def test_intent_rejects_a_blank_question() -> None:
    document = valid_study()
    document["intent"]["questions"] = ["   "]

    rejects(document)


def test_intent_rejects_an_undeclared_field() -> None:
    document = valid_study()
    document["intent"]["hidden_instruction"] = "must not enter the contract"

    rejects(document)


def test_matrix_rejects_duplicate_scenario_references() -> None:
    document = valid_study()
    document["scenario_refs"].append(deepcopy(document["scenario_refs"][0]))

    rejects(document)


def test_matrix_rejects_a_reference_in_the_wrong_contract_slot() -> None:
    document = valid_study()
    document["goal_ref"] = deepcopy(document["scenario_refs"][0])

    rejects(document)


def test_matrix_rejects_non_positive_repetitions() -> None:
    document = valid_study()
    document["repetitions"] = 0

    rejects(document)


def test_matrix_rejects_a_fixed_strategy_without_a_seed() -> None:
    document = valid_study()
    document["seed_strategy"] = {"kind": "fixed", "seed": None}

    rejects(document)


def test_matrix_rejects_a_deterministic_strategy_with_an_explicit_seed() -> None:
    document = valid_study()
    document["seed_strategy"] = {"kind": "deterministic", "seed": 7}

    rejects(document)


def test_matrix_rejects_a_comparison_with_an_unknown_variant() -> None:
    document = valid_study()
    document["comparisons"][0]["candidate_variant"] = "unknown"

    rejects(document)


def test_matrix_rejects_a_comparison_of_the_same_variant() -> None:
    document = valid_study()
    baseline = document["comparisons"][0]["baseline_variant"]
    document["comparisons"][0]["candidate_variant"] = baseline

    rejects(document)


def test_matrix_rejects_a_primary_variable_outside_typed_slots() -> None:
    document = valid_study()
    document["comparisons"][0]["primary_variable"] = "untyped-variable"

    rejects(document)


def test_matrix_rejects_a_controlled_study_without_a_comparison() -> None:
    document = valid_study()
    document["comparisons"] = []

    rejects(document)


def test_matrix_rejects_confounders_outside_an_exploratory_study() -> None:
    document = valid_study()
    document["variants"][0]["confounders"] = ["provider changed"]

    rejects(document)
