from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_data_path

from evidrun.providers import ProviderProfile


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    database_path: Path
    artifacts_dir: Path
    default_provider: ProviderProfile
    authority_enabled: bool = False

    @classmethod
    def load(cls, data_dir: Path | None = None) -> Settings:
        configured = data_dir or (
            Path(os.environ["EVIDRUN_DATA_DIR"]) if "EVIDRUN_DATA_DIR" in os.environ else None
        )
        root = configured or user_data_path("Evidrun", "Evidrun", ensure_exists=False)
        root = root.expanduser().resolve()
        return cls(
            data_dir=root,
            database_path=root / "evidrun.db",
            artifacts_dir=root / "artifacts",
            default_provider=ProviderProfile.load_default(),
            authority_enabled=os.environ.get("EVIDRUN_AUTHORITY", "").strip() in {"1", "true"},
        )

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
