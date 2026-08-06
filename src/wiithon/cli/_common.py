from __future__ import annotations

import json
import sys
from enum import Enum
from pathlib import Path
from typing import NoReturn, Optional, Annotated

import typer
from rich.console import Console

from wiithon import WiiPartType
from wiithon import WiiIsoReader
from wiithon.disc.structs.partition_entry import WiiPartitionEntry

console = Console()
err_console = Console(stderr=True, style="bold red")

JsonOption = Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON on stdout.")]


class PartTypeChoice(str, Enum):
    data = "data"
    update = "update"
    channel = "channel"

def abort(msg: str) -> NoReturn:
    err_console.print(f"Error: {msg}")
    raise typer.Exit(code=1)


def require_file(path: Path) -> None:
    if not path.exists():
        abort(f"{path} does not exist.")
    if not path.is_file():
        abort(f"{path} is not a file.")


def select_partitions(
    reader: WiiIsoReader,
    partition_type: Optional[PartTypeChoice],
) -> list[WiiPartitionEntry]:
    """Return the partitions matching partition_type, or all of them if None."""
    if partition_type is None:
        return list(reader.partitions)

    wanted = WiiPartType[partition_type.name.upper()]
    candidates = [p for p in reader.partitions if p.part_type == wanted]
    if not candidates:
        abort(f"No {partition_type.name} partition found.")

    return candidates

def write_json(data) -> None:
    sys.stdout.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")