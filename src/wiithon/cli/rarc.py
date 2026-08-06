from __future__ import annotations

from io import BytesIO

import typer

from pathlib import Path
from typing import Annotated

from rich.panel import Panel
from rich.table import Table

from wiithon import Rarc, Yaz0
from wiithon.cli._common import console, require_file, abort

rarc_app = typer.Typer(help="Operations on RARC files.")

def _read_rarc(path: Path) -> Rarc:
    """Read a RARC archive, transparently decompressing Yaz0 if needed."""
    data = path.read_bytes()
    if data[:4] == b"Yaz0":
        data = Yaz0.read(BytesIO(data)).data

    return Rarc.read(BytesIO(data))

@rarc_app.command("info")
def rarc_infos(
    rarc: Annotated[Path, typer.Argument(help="Path to the RARC archive.")],
) -> None:
    """Print information and list files about a RARC archive"""
    require_file(rarc)
    from wiithon.formats.rarc import NodeAttribute

    arc = _read_rarc(rarc)
    table = Table("Name", "Size (in bytes)", "ID")
    for entry in arc.entries:
        if entry.file_id != 0xFFFF and not entry.attributes & NodeAttribute.DIRECTORY:
            table.add_row(entry.name, f"{str(len(entry.data))}", str(entry.file_id))

    console.print(Panel(table, title=f"[bold]{rarc.name}[/bold]", expand=False))

@rarc_app.command("extract")
def rarc_extract(
    rarc: Annotated[Path, typer.Argument(help="Path to the RARC archive.")],
    dest: Annotated[Path, typer.Argument(help="Output directory.")],
) -> None:
    """Extract all files from a RARC archive"""
    require_file(rarc)
    dest.mkdir(parents=True, exist_ok=True)
    from wiithon.formats.rarc import NodeAttribute
    arc = _read_rarc(rarc)
    arc.extract_to(str(dest))

    count = sum(1 for e in arc.entries if e.file_id != 0xFFFF and not e.attributes & NodeAttribute.DIRECTORY)
    console.print(f"[green](★‿★)[/green] Extracted {count} file(s) to [bold]{dest}[/bold]")
