from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from evidrun.authority.policy import AuthorityMode, AuthorityPolicyError
from evidrun.authority.repository import (
    AuthorityRepository,
    ChallengeUnavailable,
    CredentialUnavailable,
    EnrolledCredential,
    IssuedChallenge,
)
from evidrun.authority.service import HumanAuthorityService
from evidrun.authority.subject import EvaluationDecisionSubject, RevisionDecisionSubject
from evidrun.contracts.authority import HumanAttestationError
from evidrun.infrastructure.database.repository import Repository


class ChallengePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    challenge_id: str
    challenge_digest: str
    nonce: str
    expires_at_iso: str

    def to_issued(self) -> IssuedChallenge:
        return IssuedChallenge(
            challenge_id=self.challenge_id,
            challenge_digest=self.challenge_digest,
            nonce=self.nonce,
            expires_at_iso=self.expires_at_iso,
        )


class EnrollRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    principal_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    relying_party_id: str = Field(min_length=1)
    origin: str = Field(min_length=1)


class BeginRevisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: AuthorityMode = AuthorityMode.PRIVILEGED
    credential_id: str = Field(min_length=1)
    subject: RevisionDecisionSubject


class CompleteRevisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    credential_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    subject: RevisionDecisionSubject
    challenge: ChallengePayload
    assertion: dict[str, Any]


class BeginEvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: AuthorityMode = AuthorityMode.PRIVILEGED
    credential_id: str = Field(min_length=1)
    subject: EvaluationDecisionSubject


class CompleteEvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    credential_id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    subject: EvaluationDecisionSubject
    challenge: ChallengePayload
    assertion: dict[str, Any]


def _credential_view(credential: EnrolledCredential) -> dict[str, Any]:
    return {
        "credential_id": credential.credential_id,
        "principal_id": credential.principal_id,
        "display_name": credential.display_name,
        "relying_party_id": credential.relying_party_id,
        "origin": credential.origin,
        "status": credential.status,
    }


def _challenge_view(challenge: IssuedChallenge) -> dict[str, Any]:
    return {
        "challenge_id": challenge.challenge_id,
        "challenge_digest": challenge.challenge_digest,
        "nonce": challenge.nonce,
        "expires_at_iso": challenge.expires_at_iso,
    }


def create_authority_router(
    *,
    service: HumanAuthorityService,
    authority_repository: AuthorityRepository,
    repository: Repository,
    authorize: Callable[..., Any],
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/authority", tags=["authority"])

    @router.post("/credentials")
    async def enroll(payload: EnrollRequest, _: None = Depends(authorize)) -> dict[str, Any]:
        credential = service.enroll(
            principal_id=payload.principal_id,
            display_name=payload.display_name,
            relying_party_id=payload.relying_party_id,
            origin=payload.origin,
        )
        return _credential_view(credential)

    @router.get("/credentials")
    async def credentials(_: None = Depends(authorize)) -> list[dict[str, Any]]:
        return [_credential_view(item) for item in authority_repository.list_credentials()]

    @router.post("/credentials/{credential_id}/revoke")
    async def revoke(credential_id: str, _: None = Depends(authorize)) -> dict[str, Any]:
        try:
            return _credential_view(authority_repository.revoke_credential(credential_id))
        except CredentialUnavailable as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.post("/revisions/confirmations")
    async def begin_revision(
        payload: BeginRevisionRequest, _: None = Depends(authorize)
    ) -> dict[str, Any]:
        try:
            challenge = service.begin_confirmation(
                mode=payload.mode,
                subject=payload.subject,
                credential_id=payload.credential_id,
            )
        except AuthorityPolicyError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except CredentialUnavailable as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _challenge_view(challenge)

    @router.post("/revisions/decisions")
    async def complete_revision(
        payload: CompleteRevisionRequest, _: None = Depends(authorize)
    ) -> dict[str, Any]:
        try:
            attestation = service.complete_confirmation(
                subject=payload.subject,
                credential_id=payload.credential_id,
                challenge=payload.challenge.to_issued(),
                assertion=payload.assertion,
                project_id=payload.project_id,
            )
            decision = payload.subject.build_decision(attestation)
            row = repository.registry.decide_contract_revision(decision)
        except (ChallengeUnavailable, CredentialUnavailable) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except HumanAttestationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except (ValueError, PermissionError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {
            "id": row.id,
            "decision": row.decision,
            "attestation_id": attestation.attestation_id,
        }

    @router.post("/evaluations/confirmations")
    async def begin_evaluation(
        payload: BeginEvaluationRequest, _: None = Depends(authorize)
    ) -> dict[str, Any]:
        try:
            challenge = service.begin_confirmation(
                mode=payload.mode,
                subject=payload.subject,
                credential_id=payload.credential_id,
            )
        except AuthorityPolicyError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except CredentialUnavailable as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return _challenge_view(challenge)

    @router.post("/evaluations/records")
    async def complete_evaluation(
        payload: CompleteEvaluationRequest, _: None = Depends(authorize)
    ) -> dict[str, Any]:
        try:
            attestation = service.complete_confirmation(
                subject=payload.subject,
                credential_id=payload.credential_id,
                challenge=payload.challenge.to_issued(),
                assertion=payload.assertion,
                project_id=payload.project_id,
            )
            record = payload.subject.build_evaluation(attestation)
            row = repository.evaluation.save_evaluation_record(record)
        except (ChallengeUnavailable, CredentialUnavailable) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except HumanAttestationError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except (ValueError, PermissionError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {
            "id": row.id,
            "source_type": record.source_type,
            "attestation_id": attestation.attestation_id,
        }

    return router
