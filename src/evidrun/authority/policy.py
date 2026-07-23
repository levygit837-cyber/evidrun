from __future__ import annotations

from enum import StrEnum


class AuthorityMode(StrEnum):
    """Autonomy modes and the authority they may exercise.

    Authentication is optional for creating, testing, and running in sandbox. It is
    mandatory only when the system makes a human-authority claim, releases higher
    risk, or promotes evidence to a verified state.
    """

    SANDBOX = "sandbox"
    CREATE = "create"
    TEST = "test"
    EXECUTE = "execute"
    PRIVILEGED = "privileged"


class ActionRisk(StrEnum):
    ROUTINE = "routine"
    CRITICAL = "critical"


# Critical actions can never be performed by an agent or machine; they always
# require a verified human, regardless of mode.
CRITICAL_ACTIONS: frozenset[str] = frozenset(
    {
        "revision.accepted",
        "revision.rejected",
        "revision.superseded",
        "evaluation.adjudicated",
        "evaluation.reviewed",
        "external_effect.authorized",
    }
)


class AuthorityPolicyError(PermissionError):
    """A privileged action was attempted without verified human authority."""


class AuthorityPolicy:
    """Decides whether an action requires verified human authority."""

    def action_risk(self, action: str) -> ActionRisk:
        return ActionRisk.CRITICAL if action in CRITICAL_ACTIONS else ActionRisk.ROUTINE

    def requires_verified_human(self, *, mode: AuthorityMode, action: str) -> bool:
        if self.action_risk(action) is ActionRisk.CRITICAL:
            return True
        # Routine actions in sandbox/create/test/execute stay unauthenticated.
        return mode is AuthorityMode.PRIVILEGED

    def enforce(self, *, mode: AuthorityMode, action: str, verified_human: bool) -> None:
        if self.requires_verified_human(mode=mode, action=action) and not verified_human:
            raise AuthorityPolicyError(
                f"action '{action}' in mode '{mode}' requires verified human authority"
            )
