from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCANNER = ROOT / "scripts" / "check_import_directions.py"


def write_tracked(root: Path, files: dict[str, str]) -> None:
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", *files], check=True)


def run_scanner(root: Path, *, output_format: str = "json") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCANNER),
            "--root",
            str(root),
            "--format",
            output_format,
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def test_json_reports_only_the_forbidden_tracked_python_import(tmp_path: Path) -> None:
    write_tracked(
        tmp_path,
        {
            "src/evidrun/contracts/allowed.py": (
                "from evidrun.shared.types import canonical_json\n"
            ),
            "src/evidrun/contracts/forbidden.py": (
                "from evidrun.runs import EvidrunService as Service\n"
            ),
        },
    )

    result = run_scanner(tmp_path)

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report == {
        "schema_version": "1",
        "scanned_files": 2,
        "violations": [
            {
                "source": "src/evidrun/contracts/forbidden.py",
                "destination": "evidrun.runs",
                "rule": "PY-CONTRACTS-LAYERS",
                "chain": [
                    "evidrun.contracts.forbidden",
                    "evidrun.runs",
                ],
            }
        ],
    }


def test_reexport_resolves_to_the_forbidden_destination_with_a_short_chain(
    tmp_path: Path,
) -> None:
    write_tracked(
        tmp_path,
        {
            "src/evidrun/contracts/consumer.py": "from evidrun.facade import runtime\n",
            "src/evidrun/facade/__init__.py": (
                "from evidrun.runs import service as runtime\n"
            ),
            "src/evidrun/runs/service.py": "SERVICE = object()\n",
        },
    )

    result = run_scanner(tmp_path)

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["violations"] == [
        {
            "source": "src/evidrun/contracts/consumer.py",
            "destination": "evidrun.runs.service",
            "rule": "PY-CONTRACTS-LAYERS",
            "chain": [
                "evidrun.contracts.consumer",
                "evidrun.facade",
                "evidrun.runs.service",
            ],
        }
    ]


def test_relative_reexport_from_package_init_uses_the_package_as_its_base(
    tmp_path: Path,
) -> None:
    write_tracked(
        tmp_path,
        {
            "src/evidrun/contracts/consumer.py": "from evidrun.facade import runtime\n",
            "src/evidrun/facade/__init__.py": "from ..runs import service as runtime\n",
            "src/evidrun/runs/service.py": "SERVICE = object()\n",
        },
    )

    result = run_scanner(tmp_path)

    assert result.returncode == 1
    assert json.loads(result.stdout)["violations"] == [
        {
            "source": "src/evidrun/contracts/consumer.py",
            "destination": "evidrun.runs.service",
            "rule": "PY-CONTRACTS-LAYERS",
            "chain": [
                "evidrun.contracts.consumer",
                "evidrun.facade",
                "evidrun.runs.service",
            ],
        }
    ]


def test_chained_reexports_are_followed_until_the_forbidden_layer(tmp_path: Path) -> None:
    write_tracked(
        tmp_path,
        {
            "src/evidrun/contracts/consumer.py": "from evidrun.facade_a import runtime\n",
            "src/evidrun/facade_a/__init__.py": (
                "from evidrun.facade_b import runtime\n"
            ),
            "src/evidrun/facade_b/__init__.py": (
                "from evidrun.runs import service as runtime\n"
            ),
            "src/evidrun/runs/service.py": "SERVICE = object()\n",
        },
    )

    result = run_scanner(tmp_path)

    assert result.returncode == 1
    assert json.loads(result.stdout)["violations"] == [
        {
            "source": "src/evidrun/contracts/consumer.py",
            "destination": "evidrun.runs.service",
            "rule": "PY-CONTRACTS-LAYERS",
            "chain": [
                "evidrun.contracts.consumer",
                "evidrun.facade_a",
                "evidrun.facade_b",
                "evidrun.runs.service",
            ],
        }
    ]


def test_wildcard_reexports_preserve_the_requested_symbol_across_the_chain(
    tmp_path: Path,
) -> None:
    write_tracked(
        tmp_path,
        {
            "src/evidrun/contracts/consumer.py": "from evidrun.facade_a import runtime\n",
            "src/evidrun/facade_a/__init__.py": "from evidrun.facade_b import *\n",
            "src/evidrun/facade_b/__init__.py": (
                "from evidrun.runs import service as runtime\n"
            ),
            "src/evidrun/runs/service.py": "SERVICE = object()\n",
        },
    )

    result = run_scanner(tmp_path)

    assert result.returncode == 1
    assert json.loads(result.stdout)["violations"] == [
        {
            "source": "src/evidrun/contracts/consumer.py",
            "destination": "evidrun.runs.service",
            "rule": "PY-CONTRACTS-LAYERS",
            "chain": [
                "evidrun.contracts.consumer",
                "evidrun.facade_a",
                "evidrun.facade_b",
                "evidrun.runs.service",
            ],
        }
    ]


def test_relative_import_is_resolved_before_shared_layer_policy(tmp_path: Path) -> None:
    write_tracked(
        tmp_path,
        {
            "src/evidrun/contracts/base.py": "VALUE = 1\n",
            "src/evidrun/shared/nested.py": (
                "from ..contracts import base as contract_base\n"
            ),
        },
    )

    result = run_scanner(tmp_path)

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["violations"] == [
        {
            "source": "src/evidrun/shared/nested.py",
            "destination": "evidrun.contracts.base",
            "rule": "PY-SHARED-UPWARD",
            "chain": ["evidrun.shared.nested", "evidrun.contracts.base"],
        }
    ]


def test_renderer_native_import_is_reported_without_string_or_untracked_false_positives(
    tmp_path: Path,
) -> None:
    write_tracked(
        tmp_path,
        {
            "apps/web/src/allowed.ts": (
                "/*\n"
                'import { ipcRenderer } from "electron";\n'
                "*/\n"
                'const example = \'import { ipcRenderer } from "electron"\';\n'
                "const continued = 'prefix\\\n"
                'import fs from "node:fs";\';\n'
                "const template = `\n"
                'import { readFile } from "node:fs";\n'
                "`;\n"
                "const rendered = <pre>\n"
                'import fs from "node:fs";\n'
                "</pre>;\n"
                "const custom = <CodeBlock>\n"
                'import electron from "electron";\n'
                "</CodeBlock>;\n"
                "const fragment = <>\n"
                'import path from "node:path";\n'
                "</>;\n"
                "const nested = <div><div>ok</div>\n"
                'import os from "node:os";\n'
                "</div>;\n"
            ),
            "apps/web/src/forbidden.ts": (
                "import {\n"
                "  readFile,\n"
                "  writeFile,\n"
                '} from "node:fs";\n'
            ),
        },
    )
    untracked = tmp_path / "apps/web/src/untracked.ts"
    untracked.write_text('import { ipcRenderer } from "electron";\n', encoding="utf-8")

    result = run_scanner(tmp_path)

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["scanned_files"] == 2
    assert report["violations"] == [
        {
            "source": "apps/web/src/forbidden.ts",
            "destination": "node:fs",
            "rule": "TS-RENDERER-NATIVE",
            "chain": ["apps/web/src/forbidden.ts", "node:fs"],
        }
    ]


def test_renderer_relative_import_resolves_the_versioned_cts_preload(tmp_path: Path) -> None:
    write_tracked(
        tmp_path,
        {
            "apps/desktop/src/preload/index.cts": "export const api = {};\n",
            "apps/web/src/bad.ts": (
                'import { api } from "../../desktop/src/preload/index.cjs";\n'
            ),
        },
    )

    result = run_scanner(tmp_path)

    assert result.returncode == 1
    assert json.loads(result.stdout)["violations"] == [
        {
            "source": "apps/web/src/bad.ts",
            "destination": "apps/desktop/src/preload/index.cts",
            "rule": "TS-RENDERER-NATIVE",
            "chain": [
                "apps/web/src/bad.ts",
                "apps/desktop/src/preload/index.cts",
            ],
        }
    ]


def test_renderer_static_commonjs_requires_are_reported(tmp_path: Path) -> None:
    write_tracked(
        tmp_path,
        {
            "apps/web/src/import-assignment.cts": (
                'import electron = require("electron");\n'
            ),
            "apps/web/src/require-declaration.cts": (
                'const fs = require("node:fs");\n'
            ),
        },
    )

    result = run_scanner(tmp_path)

    assert result.returncode == 1
    assert [item["destination"] for item in json.loads(result.stdout)["violations"]] == [
        "electron",
        "node:fs",
    ]


def test_renderer_require_inside_jsx_expression_is_not_masked(tmp_path: Path) -> None:
    write_tracked(
        tmp_path,
        {
            "apps/web/src/bad.tsx": (
                "const rendered = <div>{(() => {\n"
                '  const fs = require("node:fs");\n'
                "  return null;\n"
                "})()}</div>;\n"
            ),
        },
    )

    result = run_scanner(tmp_path)

    assert result.returncode == 1
    assert json.loads(result.stdout)["violations"][0]["destination"] == "node:fs"


def test_electron_main_cannot_import_renderer_domain_modules(tmp_path: Path) -> None:
    write_tracked(
        tmp_path,
        {
            "apps/desktop/src/main/bad.ts": (
                'import { CreatePage } from "../../../web/src/features/create/CreatePage";\n'
            ),
            "apps/web/src/features/create/CreatePage.tsx": (
                "export const CreatePage = () => null;\n"
            ),
        },
    )

    result = run_scanner(tmp_path)

    assert result.returncode == 1
    assert json.loads(result.stdout)["violations"] == [
        {
            "source": "apps/desktop/src/main/bad.ts",
            "destination": "apps/web/src/features/create/CreatePage.tsx",
            "rule": "TS-MAIN-DOMAIN",
            "chain": [
                "apps/desktop/src/main/bad.ts",
                "apps/web/src/features/create/CreatePage.tsx",
            ],
        }
    ]


def test_namespace_policy_uses_component_boundaries(tmp_path: Path) -> None:
    write_tracked(
        tmp_path,
        {
            "src/evidrun/infrastructure/allowed.py": "import evidrun.runstats\n",
            "src/evidrun/shared/forbidden.py": "import evidrun.sharedness\n",
        },
    )

    result = run_scanner(tmp_path)

    assert result.returncode == 1
    assert json.loads(result.stdout)["violations"] == [
        {
            "source": "src/evidrun/shared/forbidden.py",
            "destination": "evidrun.sharedness",
            "rule": "PY-SHARED-UPWARD",
            "chain": ["evidrun.shared.forbidden", "evidrun.sharedness"],
        }
    ]


def test_exception_requires_reason_owner_and_expiry(tmp_path: Path) -> None:
    write_tracked(
        tmp_path,
        {
            "src/evidrun/contracts/forbidden.py": "from evidrun.runs import service\n",
        },
    )
    (tmp_path / "import-directions.toml").write_text(
        """
schema_version = "1"

[[exceptions]]
source = "src/evidrun/contracts/forbidden.py"
destination = "evidrun.runs"
rule = "PY-CONTRACTS-LAYERS"
reason = "temporary migration"
""".lstrip(),
        encoding="utf-8",
    )

    result = run_scanner(tmp_path, output_format="text")

    assert result.returncode == 2
    assert "exception 1 missing: expires, owner" in result.stderr


def test_exception_rejects_blank_metadata_and_datetime_expiry(tmp_path: Path) -> None:
    write_tracked(
        tmp_path,
        {
            "src/evidrun/contracts/forbidden.py": "from evidrun.runs import service\n",
        },
    )
    (tmp_path / "import-directions.toml").write_text(
        """
schema_version = "1"

[[exceptions]]
source = "src/evidrun/contracts/forbidden.py"
destination = "evidrun.runs"
rule = "PY-CONTRACTS-LAYERS"
reason = "   "
owner = "core"
expires = 2099-01-01T00:00:00Z
""".lstrip(),
        encoding="utf-8",
    )

    result = run_scanner(tmp_path, output_format="text")

    assert result.returncode == 2
    assert "exception 1 field reason must be a non-empty string" in result.stderr


def test_exception_rejects_datetime_expiry_even_with_valid_metadata(tmp_path: Path) -> None:
    write_tracked(
        tmp_path,
        {
            "src/evidrun/contracts/forbidden.py": "from evidrun.runs import service\n",
        },
    )
    (tmp_path / "import-directions.toml").write_text(
        """
schema_version = "1"

[[exceptions]]
source = "src/evidrun/contracts/forbidden.py"
destination = "evidrun.runs"
rule = "PY-CONTRACTS-LAYERS"
reason = "temporary migration"
owner = "core"
expires = 2099-01-01T00:00:00Z
""".lstrip(),
        encoding="utf-8",
    )

    result = run_scanner(tmp_path, output_format="text")

    assert result.returncode == 2
    assert "exception 1 expires must be a TOML date or ISO date string" in result.stderr


def test_exact_exception_is_audited_and_does_not_hide_a_new_violation(tmp_path: Path) -> None:
    write_tracked(
        tmp_path,
        {
            "src/evidrun/contracts/known.py": "from evidrun.runs import service\n",
            "src/evidrun/contracts/new.py": "from evidrun.infrastructure import database\n",
        },
    )
    (tmp_path / "import-directions.toml").write_text(
        """
schema_version = "1"

[[exceptions]]
source = "src/evidrun/contracts/known.py"
destination = "evidrun.runs"
rule = "PY-CONTRACTS-LAYERS"
reason = "migration owned by issue 999"
owner = "core"
expires = 2099-01-01
""".lstrip(),
        encoding="utf-8",
    )

    result = run_scanner(tmp_path, output_format="text")

    assert result.returncode == 1
    assert (
        "EXCEPTION PY-CONTRACTS-LAYERS: src/evidrun/contracts/known.py -> "
        "evidrun.runs owner=core expires=2099-01-01 reason=migration owned by issue 999"
    ) in result.stdout
    assert "src/evidrun/contracts/new.py -> evidrun.infrastructure" in result.stderr
