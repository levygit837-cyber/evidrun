from __future__ import annotations

import pytest

from evidrun.authority.policy import (
    ActionRisk,
    AuthorityMode,
    AuthorityPolicy,
    AuthorityPolicyError,
)

CRITICAL = [
    "revision.accepted",
    "revision.rejected",
    "revision.superseded",
    "evaluation.adjudicated",
    "evaluation.reviewed",
    "external_effect.authorized",
]


@pytest.fixture
def policy() -> AuthorityPolicy:
    return AuthorityPolicy()


@pytest.mark.parametrize("action", CRITICAL)
@pytest.mark.parametrize("mode", list(AuthorityMode))
def test_critical_actions_always_require_verified_human(
    policy: AuthorityPolicy, action: str, mode: AuthorityMode
) -> None:
    assert policy.action_risk(action) is ActionRisk.CRITICAL
    assert policy.requires_verified_human(mode=mode, action=action) is True
    with pytest.raises(AuthorityPolicyError):
        policy.enforce(mode=mode, action=action, verified_human=False)
    policy.enforce(mode=mode, action=action, verified_human=True)


@pytest.mark.parametrize(
    "mode",
    [AuthorityMode.SANDBOX, AuthorityMode.CREATE, AuthorityMode.TEST, AuthorityMode.EXECUTE],
)
def test_routine_actions_are_unauthenticated_outside_privileged(
    policy: AuthorityPolicy, mode: AuthorityMode
) -> None:
    assert policy.requires_verified_human(mode=mode, action="run.execute") is False
    policy.enforce(mode=mode, action="run.execute", verified_human=False)


def test_privileged_mode_gates_even_routine_actions(policy: AuthorityPolicy) -> None:
    assert (
        policy.requires_verified_human(
            mode=AuthorityMode.PRIVILEGED, action="run.execute"
        )
        is True
    )
    with pytest.raises(AuthorityPolicyError):
        policy.enforce(
            mode=AuthorityMode.PRIVILEGED, action="run.execute", verified_human=False
        )
