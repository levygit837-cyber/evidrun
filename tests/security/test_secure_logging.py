from __future__ import annotations

import json
import logging

import pytest

from evidrun.security import emit_secure_log, safe_log_document


def test_python_log_keeps_operational_identity_without_sensitive_material(
    caplog: pytest.LogCaptureFixture,
) -> None:
    logger = logging.getLogger("evidrun.security.fixture")
    secret = "fixture-secret-must-never-be-logged"
    error = RuntimeError(f"Authorization: Bearer {secret}")

    with caplog.at_level(logging.ERROR, logger=logger.name):
        emit_secure_log(
            logger,
            logging.ERROR,
            "provider.request.failed",
            correlation_id="run_fixture_01",
            error_code="provider.transport_error",
            error=error,
            fields={
                "provider_id": "cliproxyapi-local",
                "status_code": 503,
                "authorization": f"Bearer {secret}",
                "cookie": f"session={secret}",
                "environment": {"EVIDRUN_PROVIDER_API_KEY": secret},
                "prompt": secret,
                "subject_envelope": {"input": secret},
                "actor": "claimed-human",
            },
        )

    document = json.loads(caplog.records[0].getMessage())
    assert document == {
        "correlation_id": "run_fixture_01",
        "error_code": "provider.transport_error",
        "error_type": "RuntimeError",
        "event_code": "provider.request.failed",
        "provider_id": "cliproxyapi-local",
        "status_code": 503,
    }
    assert secret not in caplog.text
    assert "claimed-human" not in caplog.text


def test_python_log_redacts_secret_shaped_values_in_allowed_fields() -> None:
    api_key = "sk-proj-" + "A" * 32

    document = safe_log_document(
        "provider.request.failed",
        correlation_id=api_key,
        error_code=api_key,
        fields={"provider_id": api_key},
    )

    assert document == {
        "correlation_id": "<redacted>",
        "error_code": "<redacted>",
        "event_code": "provider.request.failed",
        "provider_id": "<redacted>",
    }
    assert api_key not in json.dumps(document)
