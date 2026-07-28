"""Console entrypoint for the durable Run executor.

Two ways in. A terminal passes `--data-dir`. A supervising desktop shell passes
`--desktop-handshake` and writes the data dir on stdin instead, because a database path
in argv is visible to every other process on the machine.

Either way this only wires up `DurableRunWorker`; claim, heartbeat, fencing and terminal
semantics stay where ADR 0014 put them.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import socket
import sys
from contextlib import suppress
from pathlib import Path

from evidrun.infrastructure.database import Database, Repository
from evidrun.runs import DurableRunWorker, build_runtime_kernel
from evidrun.settings import Settings
from evidrun.shared.types import new_id

WORKER_PROTOCOL = "evidrun-worker-v1"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evidrun durable Run worker")
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--worker-id")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll-interval", type=float, default=1.0)
    parser.add_argument("--lease-seconds", type=float, default=30.0)
    parser.add_argument("--heartbeat-seconds", type=float, default=10.0)
    parser.add_argument(
        "--desktop-handshake",
        action="store_true",
        help="read the data dir from stdin and announce readiness on stdout",
    )
    return parser


def read_handshake() -> Path | None:
    """Take the data dir off stdin, keeping it out of argv.

    A supervisor that sends nothing usable gets `None` and the ordinary data dir
    resolution, rather than a worker guessing at a path.
    """

    line = sys.stdin.readline()
    if not line.strip():
        return None
    handshake = json.loads(line)
    data_dir = handshake.get("data_dir")
    return Path(str(data_dir)) if data_dir else None


def announce_ready(worker_id: str) -> None:
    """Tell the supervisor the executor is polling, mirroring the backend banner.

    The worker id is operational identity, not a secret: it is already written to every
    attempt row. The data dir is deliberately absent.
    """

    print(
        json.dumps(
            {
                "protocol": WORKER_PROTOCOL,
                "schema_version": "1",
                "pid": os.getpid(),
                "worker_id": worker_id,
            }
        ),
        flush=True,
    )


async def run_worker(
    args: argparse.Namespace, repository: Repository, data_dir: Path | None
) -> None:
    settings = Settings.load(data_dir)
    kernel = build_runtime_kernel(repository, settings.artifacts_dir)
    worker_id = args.worker_id or (
        f"{socket.gethostname()}:{os.getpid()}:{new_id('worker')}"
    )
    worker = DurableRunWorker(
        repository,
        kernel.coordinator,
        worker_id=worker_id,
        lease_seconds=args.lease_seconds,
        heartbeat_seconds=args.heartbeat_seconds,
        poll_interval=args.poll_interval,
    )
    if args.once:
        await worker.process_once()
        return
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(signum, stop.set)
    if args.desktop_handshake:
        announce_ready(worker_id)
    await worker.run_forever(stop)


def main() -> None:
    args = build_parser().parse_args()
    data_dir = read_handshake() if args.desktop_handshake else args.data_dir
    settings = Settings.load(data_dir)
    settings.ensure_directories()
    database = Database(settings.database_path)
    database.create_all()
    repository = Repository(database)
    try:
        asyncio.run(run_worker(args, repository, data_dir))
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
