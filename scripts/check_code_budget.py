"""Gate de orçamento estrutural dos arquivos versionados.

Mede três métricas por arquivo rastreado pelo git e compara com o orçamento do
grupo de globs a que o arquivo pertence:

- `file_lines`: linhas do arquivo;
- `function_lines`: maior função ou método (só Python, via `ast`);
- `public_methods`: maior número de métodos públicos de uma classe (só Python).

Arquivos que já violavam a política quando o gate foi ligado ficam na tabela
`[baseline]` de `code-budget.toml`. O baseline é um ratchet: uma métrica listada
pode encolher, nunca crescer, e quando volta para dentro do orçamento normal o
gate exige a remoção da entrada.

Um arquivo que passa de `warn_at_ratio` do seu orçamento recebe AVISO, sem falhar
o gate. O aviso existe para que a próxima capability não empurre um arquivo
recém-extraído de volta para o baseline sem ninguém notar antes.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from code_budget import (
    CONFIG_NAME,
    Finding,
    check,
    load_policy,
    measure_all,
    tracked_files,
    update_baseline,
    violations,
    warnings,
)

ROOT: Final = Path(__file__).resolve().parents[1]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_code_budget",
        description="Verifica o orçamento de tamanho de arquivo, função e classe.",
    )
    parser.add_argument("--root", type=Path, default=ROOT, help="raiz do repositório")
    parser.add_argument(
        "--config", type=Path, default=None, help=f"caminho de {CONFIG_NAME} (default: na raiz)"
    )
    parser.add_argument("--json", action="store_true", help="saída de máquina em JSON")
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="regrava o baseline a partir do estado atual (uso humano deliberado, nunca em CI)",
    )
    return parser


def _render(finding: Finding) -> str:
    limit = "sem limite" if finding.limit is None else str(finding.limit)
    label = "VIOLAÇÃO" if finding.severity == "violation" else "AVISO"
    return (
        f"{label} {finding.path}: {finding.metric}={finding.measured} "
        f"(limite {limit}) — {finding.message}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root: Path = Path(args.root).resolve()
    config_path: Path = Path(args.config) if args.config is not None else root / CONFIG_NAME
    policy = load_policy(config_path)
    measurements = measure_all(root, policy, tracked_files(root))

    if args.update_baseline:
        baseline, changes = update_baseline(config_path, policy, measurements)
        if args.json:
            print(
                json.dumps(
                    {"baseline_files": len(baseline)} | changes, ensure_ascii=False, indent=2
                )
            )
            return 0
        print(f"Baseline regravado em {config_path.name}: {len(baseline)} arquivos")
        for label, paths in changes.items():
            if paths:
                print(f"  {label}: {', '.join(paths)}")
        return 0

    findings = check(policy, measurements)
    failed = violations(findings)
    advisory = warnings(findings)
    if args.json:
        print(
            json.dumps(
                {
                    "ok": not failed,
                    "checked_files": len(measurements),
                    "baseline_files": len(policy.baseline),
                    "violations": [item.as_dict() for item in failed],
                    "warnings": [item.as_dict() for item in advisory],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1 if failed else 0
    for finding in (*advisory, *failed):
        print(_render(finding), file=sys.stderr)
    print(
        f"Orçamento estrutural: {len(measurements)} arquivos medidos, "
        f"{len(policy.baseline)} no baseline, {len(failed)} violações, "
        f"{len(advisory)} avisos",
        file=sys.stderr if failed else sys.stdout,
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
