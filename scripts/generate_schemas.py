from __future__ import annotations

import json
from pathlib import Path

from evidrun.entrypoints.api.app import create_app
from evidrun.experiments import ExperimentManifest

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "schemas" / "generated"


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "experiment-manifest-v1.json").write_text(
        json.dumps(ExperimentManifest.model_json_schema(), ensure_ascii=False, indent=2) + "\n"
    )
    app = create_app(data_dir=ROOT / ".schema-build")
    (OUTPUT / "openapi-v1.json").write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()

