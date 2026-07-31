"""Deterministic human and machine renderers for resource measurements."""

from __future__ import annotations

import json
from typing import Any


def json_document(document: dict[str, Any]) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def text_document(document: dict[str, Any]) -> str:
    lines = [f"Resource budgets — {document['profile']}"]
    for scenario in document["scenarios"]:
        for metric in scenario["metrics"]:
            value = _display_value(metric["value"])
            lines.append(
                f"{metric['status'].upper()} {scenario['id']}.{metric['name']} "
                f"= {value} {metric['unit']} [{metric['enforcement']}]"
                f"{_detail(metric)}"
            )
    summary = document["summary"]
    lines.append(
        "Summary: "
        + ", ".join(f"{name}={summary[name]}" for name in sorted(summary))
    )
    return "\n".join(lines) + "\n"


def _display_value(value: object) -> str:
    if value is None:
        return "unavailable"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _detail(metric: dict[str, Any]) -> str:
    if metric.get("reason"):
        return f" — {metric['reason']}"
    if metric["status"] == "inconclusive":
        return f" — relative_mad={metric['relative_mad']:.3f}"
    if metric["status"] == "regression":
        return f" — warning threshold={_display_value(metric['threshold'])}"
    if metric["status"] == "violation":
        bounds = [
            f"minimum={_display_value(metric['minimum'])}"
            if metric.get("minimum") is not None
            else "",
            f"limit={_display_value(metric['limit'])}" if metric.get("limit") is not None else "",
        ]
        return " — " + ", ".join(item for item in bounds if item)
    return ""
