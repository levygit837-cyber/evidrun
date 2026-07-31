from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from change_contract.openapi_diff import compare_openapi  # noqa: E402
from change_contract.schema_diff import (  # noqa: E402
    Compatibility,
    ContractSurface,
    SchemaDiffError,
    compare_json_schema,
)


def object_schema(
    properties: dict[str, object], *, required: tuple[str, ...] = ()
) -> dict[str, object]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(required),
        "additionalProperties": False,
    }


def test_optional_field_is_additive_but_required_field_is_breaking() -> None:
    baseline = object_schema({"id": {"type": "string"}}, required=("id",))

    optional = object_schema(
        {"id": {"type": "string"}, "note": {"type": "string"}},
        required=("id",),
    )
    optional_report = compare_json_schema(baseline, optional, path="schema.json")
    assert [(item.kind, item.compatibility, item.pointer) for item in optional_report.changes] == [
        ("optional-property-added", Compatibility.ADDITIVE, "/properties/note")
    ]

    required = object_schema(
        {"id": {"type": "string"}, "note": {"type": "string"}},
        required=("id", "note"),
    )
    required_report = compare_json_schema(baseline, required, path="schema.json")
    assert [(item.kind, item.compatibility, item.pointer) for item in required_report.changes] == [
        ("required-property-added", Compatibility.BREAKING, "/properties/note")
    ]


def test_removal_rename_and_type_change_are_breaking_and_legible() -> None:
    baseline = object_schema(
        {
            "display_name": {"type": "string"},
            "age": {"type": "integer"},
        }
    )
    candidate = object_schema(
        {
            "name": {"type": "string"},
            "age": {"type": "string"},
        }
    )

    report = compare_json_schema(baseline, candidate, path="person.json")

    assert report.highest_compatibility is Compatibility.BREAKING
    assert [(item.kind, item.pointer) for item in report.changes] == [
        ("property-removed", "/properties/display_name"),
        ("optional-property-added", "/properties/name"),
        ("type-changed", "/properties/age/type"),
    ]
    assert "display_name" in report.changes[0].message
    assert report.as_dict()["surface"] == "json-schema"


def test_descriptions_examples_and_property_order_do_not_change_contract() -> None:
    baseline = object_schema(
        {
            "id": {
                "type": "string",
                "description": "Old wording",
                "examples": ["one"],
            }
        }
    )
    candidate = object_schema(
        {
            "id": {
                "examples": ["two"],
                "description": "New wording",
                "type": "string",
            }
        }
    )

    report = compare_json_schema(baseline, candidate, path="schema.json")

    assert report.changes == ()
    assert report.highest_compatibility is Compatibility.COMPATIBLE


def test_enum_narrowing_and_widening_fail_closed_as_breaking() -> None:
    baseline = {"type": "string", "enum": ["queued", "running"]}
    narrowed = {"type": "string", "enum": ["queued"]}
    widened = {"type": "string", "enum": ["queued", "running", "failed"]}

    narrow_report = compare_json_schema(baseline, narrowed, path="state.json")
    wide_report = compare_json_schema(baseline, widened, path="state.json")

    assert narrow_report.changes[0].kind == "enum-values-removed"
    assert narrow_report.changes[0].compatibility is Compatibility.BREAKING
    assert wide_report.changes[0].kind == "enum-values-added"
    assert wide_report.changes[0].compatibility is Compatibility.BREAKING


def openapi(
    paths: dict[str, object], schemas: dict[str, object] | None = None
) -> dict[str, object]:
    return {
        "openapi": "3.1.0",
        "info": {"title": "Fixture", "version": "1.0.0"},
        "paths": paths,
        "components": {"schemas": schemas or {}},
    }


def test_openapi_operation_addition_and_removal_are_distinguished() -> None:
    baseline = openapi(
        {
            "/runs": {"get": {"operationId": "listRuns", "responses": {"200": {}}}},
            "/legacy": {"get": {"operationId": "legacy", "responses": {"200": {}}}},
        }
    )
    candidate = openapi(
        {
            "/runs": {
                "get": {"operationId": "listRuns", "responses": {"200": {}}},
                "post": {"operationId": "createRun", "responses": {"202": {}}},
            }
        }
    )

    report = compare_openapi(baseline, candidate, path="openapi.json")

    assert report.surface is ContractSurface.OPENAPI
    assert [(item.kind, item.compatibility, item.pointer) for item in report.changes] == [
        ("path-removed", Compatibility.BREAKING, "/paths/~1legacy"),
        ("operation-added", Compatibility.ADDITIVE, "/paths/~1runs/post"),
    ]


def test_openapi_compares_component_schemas_and_ignores_message_wording() -> None:
    baseline = openapi(
        {},
        {
            "Failure": object_schema(
                {
                    "code": {"type": "string"},
                    "message": {"type": "string", "description": "Old message"},
                },
                required=("code",),
            )
        },
    )
    wording_only = openapi(
        {},
        {
            "Failure": object_schema(
                {
                    "code": {"type": "string"},
                    "message": {"type": "string", "description": "Translated message"},
                },
                required=("code",),
            )
        },
    )
    breaking = openapi(
        {},
        {
            "Failure": object_schema(
                {
                    "code": {"type": "integer"},
                    "message": {"type": "string", "description": "Translated message"},
                },
                required=("code",),
            )
        },
    )

    assert compare_openapi(baseline, wording_only, path="openapi.json").changes == ()
    report = compare_openapi(baseline, breaking, path="openapi.json")
    assert [(item.kind, item.pointer) for item in report.changes] == [
        ("type-changed", "/components/schemas/Failure/properties/code/type")
    ]


def test_openapi_required_parameter_and_inline_response_schema_are_breaking() -> None:
    baseline = openapi(
        {
            "/runs": {
                "get": {
                    "operationId": "listRuns",
                    "parameters": [],
                    "responses": {
                        "200": {"content": {"application/json": {"schema": {"type": "string"}}}}
                    },
                }
            }
        }
    )
    candidate = openapi(
        {
            "/runs": {
                "get": {
                    "operationId": "listRuns",
                    "parameters": [
                        {
                            "name": "project",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "200": {"content": {"application/json": {"schema": {"type": "integer"}}}}
                    },
                }
            }
        }
    )

    report = compare_openapi(baseline, candidate, path="openapi.json")

    assert [(item.kind, item.compatibility) for item in report.changes] == [
        ("required-parameter-added", Compatibility.BREAKING),
        ("type-changed", Compatibility.BREAKING),
    ]


def test_openapi_path_level_required_parameter_is_breaking() -> None:
    operation = {"get": {"operationId": "listRuns", "responses": {"200": {}}}}
    baseline = openapi({"/runs": operation})
    candidate = openapi(
        {
            "/runs": {
                **operation,
                "parameters": [
                    {
                        "name": "tenant",
                        "in": "header",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                ],
            }
        }
    )

    report = compare_openapi(baseline, candidate, path="openapi.json")

    assert [(item.kind, item.compatibility, item.pointer) for item in report.changes] == [
        (
            "required-parameter-added",
            Compatibility.BREAKING,
            "/paths/~1runs/parameters/header:tenant",
        )
    ]


def test_optional_property_with_new_definition_remains_additive() -> None:
    baseline = object_schema({"id": {"type": "string"}}, required=("id",))
    candidate = {
        **object_schema(
            {
                "id": {"type": "string"},
                "meta": {"$ref": "#/$defs/Meta"},
            },
            required=("id",),
        ),
        "$defs": {
            "Meta": object_schema({"label": {"type": "string"}}),
        },
    }

    report = compare_json_schema(baseline, candidate, path="schema.json")

    assert report.highest_compatibility is Compatibility.ADDITIVE
    assert [(item.kind, item.compatibility) for item in report.changes] == [
        ("optional-property-added", Compatibility.ADDITIVE),
        ("schema-added", Compatibility.ADDITIVE),
    ]


@pytest.mark.parametrize("baseline,candidate", [([], {}), ({}, []), ({"type": "object"}, [])])
def test_invalid_document_roots_fail_closed(baseline: object, candidate: object) -> None:
    with pytest.raises(SchemaDiffError, match="objeto JSON"):
        compare_json_schema(baseline, candidate, path="invalid.json")
