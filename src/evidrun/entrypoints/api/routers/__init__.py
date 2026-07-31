"""One router per route family; each states the context it needs."""

from evidrun.entrypoints.api.routers.contracts import (
    create_admission_router,
    create_contract_router,
)
from evidrun.entrypoints.api.routers.evidence import (
    create_chat_router,
    create_comparison_router,
    create_evidence_router,
)
from evidrun.entrypoints.api.routers.platform import (
    create_catalog_router,
    create_platform_router,
)
from evidrun.entrypoints.api.routers.reviews import create_review_router
from evidrun.entrypoints.api.routers.runs import (
    create_run_read_router,
    create_run_router,
)

__all__ = [
    "create_admission_router",
    "create_catalog_router",
    "create_chat_router",
    "create_comparison_router",
    "create_contract_router",
    "create_evidence_router",
    "create_platform_router",
    "create_review_router",
    "create_run_read_router",
    "create_run_router",
]
