"""Instala os git hooks locais do repositório de forma idempotente.

Uso deliberado e manual, nunca automático:

    uv run python scripts/install_git_hooks.py

Por padrão cria um symlink relativo de `.git/hooks/<nome>` para
`scripts/hooks/<nome>`, de modo que o hook acompanhe o repositório sem cópia.
Use `--copy` em ambientes sem symlink e `--force` para substituir um hook
preexistente que não seja gerenciado por este script.
"""

from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parents[1]
SOURCE_DIR: Final = ROOT / "scripts" / "hooks"
HOOKS: Final[tuple[str, ...]] = ("pre-push",)


def hooks_dir(root: Path) -> Path:
    """Diretório real de hooks, respeitando `core.hooksPath` e worktrees."""
    completed = subprocess.run(
        ("git", "rev-parse", "--git-path", "hooks"),
        cwd=root,
        check=True,
        capture_output=True,
    )
    return (root / completed.stdout.decode("utf-8").strip()).resolve()


def _make_executable(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _is_managed(target: Path, source: Path) -> bool:
    if target.is_symlink():
        return (target.parent / os.readlink(target)).resolve() == source.resolve()
    if not target.is_file():
        return False
    return target.read_bytes() == source.read_bytes()


def install(
    root: Path, *, names: Sequence[str] = HOOKS, copy: bool = False, force: bool = False
) -> int:
    destination = hooks_dir(root)
    destination.mkdir(parents=True, exist_ok=True)
    failures = 0
    for name in names:
        source = SOURCE_DIR / name
        if not source.is_file():
            print(f"ERRO: hook de origem ausente: {source.relative_to(root)}", file=sys.stderr)
            failures += 1
            continue
        _make_executable(source)
        target = destination / name
        if target.exists() or target.is_symlink():
            if _is_managed(target, source):
                print(f"já instalado: {name} -> {source.relative_to(root)}")
                continue
            if not force:
                print(
                    f"ERRO: {target} já existe e não é gerenciado por este script; "
                    "use --force para substituir",
                    file=sys.stderr,
                )
                failures += 1
                continue
            target.unlink()
            print(f"substituindo hook preexistente: {name}")
        if copy:
            shutil.copyfile(source, target)
            _make_executable(target)
            print(f"copiado: {name} <- {source.relative_to(root)}")
            continue
        relative = Path(os.path.relpath(source, destination))
        try:
            target.symlink_to(relative)
        except OSError:
            shutil.copyfile(source, target)
            _make_executable(target)
            print(f"symlink indisponível; copiado: {name} <- {source.relative_to(root)}")
            continue
        print(f"symlink criado: {name} -> {relative}")
    return failures


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="install_git_hooks",
        description="Instala os hooks de scripts/hooks em .git/hooks (idempotente).",
    )
    parser.add_argument("--root", type=Path, default=ROOT, help="raiz do repositório")
    parser.add_argument("--copy", action="store_true", help="copiar em vez de criar symlink")
    parser.add_argument(
        "--force", action="store_true", help="substituir hook preexistente não gerenciado"
    )
    args = parser.parse_args(argv)
    failures = install(Path(args.root).resolve(), copy=bool(args.copy), force=bool(args.force))
    if failures:
        print(f"{failures} hook(s) não instalado(s)", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
