from __future__ import annotations

import argparse
import asyncio
import os
import signal
import socket
from contextlib import suppress
from pathlib import Path

from evidrun.infrastructure.database import Database, Repository
from evidrun.runs import DurableRunWorker, build_runtime_kernel
from evidrun.settings import Settings
from evidrun.shared.types import new_id


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evidrun durable Run worker")
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--worker-id")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll-interval", type=float, default=1.0)
    parser.add_argument("--lease-seconds", type=float, default=30.0)
    parser.add_argument("--heartbeat-seconds", type=float, default=10.0)
    return parser


async def run_worker(args: argparse.Namespace, repository: Repository) -> None:
    settings = Settings.load(args.data_dir)
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
    await worker.run_forever(stop)


def main() -> None:
    args = build_parser().parse_args()
    settings = Settings.load(args.data_dir)
    settings.ensure_directories()
    database = Database(settings.database_path)
    database.create_all()
    repository = Repository(database)
    try:
        asyncio.run(run_worker(args, repository))
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
