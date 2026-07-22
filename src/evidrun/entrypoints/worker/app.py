from __future__ import annotations

import time

from rich.console import Console


def main() -> None:
    console = Console()
    console.print(
        "[yellow]Worker durável reservado.[/yellow] "
        "A espinha determinística executa no coordinator local nesta revisão."
    )
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        console.print("Worker encerrado.")


if __name__ == "__main__":
    main()
