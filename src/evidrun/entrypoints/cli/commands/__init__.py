"""One module per command family; the root app only registers them."""

from evidrun.entrypoints.cli.commands.contracts import (
    contract_app,
    experiment_app,
    study_app,
)
from evidrun.entrypoints.cli.commands.provider import authority_app, provider_app
from evidrun.entrypoints.cli.commands.runs import (
    bundle_app,
    chat_app,
    data_app,
    run_app,
)
from evidrun.entrypoints.cli.commands.scopes import project_app, workspace_app

__all__ = [
    "authority_app",
    "bundle_app",
    "chat_app",
    "contract_app",
    "data_app",
    "experiment_app",
    "project_app",
    "provider_app",
    "run_app",
    "study_app",
    "workspace_app",
]
