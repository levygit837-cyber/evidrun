from __future__ import annotations

import asyncio
from contextlib import suppress

from sqlalchemy.exc import OperationalError

from evidrun.infrastructure.database import LeaseLost, Repository
from evidrun.runs.coordinator import RunExecutionCoordinator


class DurableRunWorker:
    def __init__(
        self,
        repository: Repository,
        coordinator: RunExecutionCoordinator,
        *,
        worker_id: str,
        lease_seconds: float = 30.0,
        heartbeat_seconds: float = 10.0,
        poll_interval: float = 1.0,
    ) -> None:
        if lease_seconds <= 0 or heartbeat_seconds <= 0 or poll_interval <= 0:
            raise ValueError("worker timing values must be positive")
        if heartbeat_seconds >= lease_seconds / 2:
            raise ValueError("heartbeat_seconds must be less than half the lease")
        self.repository = repository
        self.coordinator = coordinator
        self.worker_id = worker_id
        self.lease_seconds = lease_seconds
        self.heartbeat_seconds = heartbeat_seconds
        self.poll_interval = poll_interval

    async def process_once(self, *, job_id: str | None = None) -> bool:
        claim = self.repository.claim_next_job(
            worker_id=self.worker_id,
            lease_seconds=self.lease_seconds,
            job_id=job_id,
        )
        if claim is None:
            return False
        job, attempt = claim
        heartbeat = asyncio.create_task(
            self._heartbeat(job.job_id, attempt.attempt_id, attempt.lease_generation)
        )
        execution = asyncio.create_task(self.coordinator.execute_attempt(job, attempt))
        try:
            done, _ = await asyncio.wait(
                {execution, heartbeat},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if heartbeat in done:
                heartbeat_error = heartbeat.exception()
                execution.cancel()
                with suppress(asyncio.CancelledError):
                    await execution
                if isinstance(heartbeat_error, LeaseLost):
                    return True
                raise RuntimeError(
                    "worker heartbeat failed; attempt was abandoned for lease expiry"
                ) from heartbeat_error
            await execution
        except LeaseLost:
            return True
        except OperationalError:
            try:
                self.repository.release_lease(
                    job_id=job.job_id,
                    attempt_id=attempt.attempt_id,
                    worker_id=attempt.worker_id,
                    lease_generation=attempt.lease_generation,
                    reason_code="transient_storage_error",
                )
            except LeaseLost:
                return True
            except (OperationalError, ValueError) as release_error:
                raise RuntimeError(
                    "worker storage failed; attempt was left for fenced lease expiry"
                ) from release_error
            return True
        except RuntimeError as exc:
            if str(exc).startswith("worker heartbeat failed"):
                raise
            with suppress(LeaseLost):
                self.coordinator.reject_attempt(
                    job,
                    attempt,
                    reason_code="runtime_consistency_error",
                )
            return True
        except Exception:
            with suppress(LeaseLost):
                self.coordinator.reject_attempt(
                    job,
                    attempt,
                    reason_code="runtime_consistency_error",
                )
            return True
        finally:
            if not execution.done():
                execution.cancel()
                with suppress(asyncio.CancelledError):
                    await execution
            heartbeat.cancel()
            with suppress(asyncio.CancelledError, LeaseLost, OperationalError, RuntimeError):
                await heartbeat
        return True

    async def run_forever(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            processed = await self.process_once()
            if not processed:
                with suppress(TimeoutError):
                    await asyncio.wait_for(stop.wait(), timeout=self.poll_interval)

    async def _heartbeat(self, job_id: str, attempt_id: str, lease_generation: int) -> None:
        while True:
            await asyncio.sleep(self.heartbeat_seconds)
            self.repository.heartbeat_lease(
                job_id=job_id,
                attempt_id=attempt_id,
                worker_id=self.worker_id,
                lease_generation=lease_generation,
                lease_seconds=self.lease_seconds,
            )
