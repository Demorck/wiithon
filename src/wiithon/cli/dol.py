from __future__ import annotations
import typer

from pathlib import Path
from typing import Annotated, Optional

from rich.panel import Panel
from rich.table import Table

from wiithon.cli._common import PartTypeChoice, console, require_file, select_partitions

dol_app = typer.Typer(help="Operations on DOL files.")

@dol_app.command("caves")
def dol_caves(
    iso: Annotated[Path, typer.Argument(help="Path to the Wii ISO")],
    min_size: Annotated[int, typer.Option("--min-size", "-m", help="The minimum size of the cave")] = 0x20,
    partition_type: Annotated[
        Optional[PartTypeChoice], typer.Option("--partition", "-p", help="Choose the partition type to list")
    ] = None
) -> None:
    """Find all code caves in a dol file"""
    require_file(iso)

    from wiithon.disc.reader import WiiIsoReader

    with WiiIsoReader(str(iso)) as reader:
        for partition in select_partitions(reader, partition_type):
            part = reader.open_partition(partition)
            dol = part.read_dol()
            table = Table("Section type", "Section number", "Start address", "Length")

            for section, addr, size in dol.find_code_caves(min_size):
                sections = section.split("[")
                section_type = sections[0]
                section_number = sections[1].split("]")[0]
                table.add_row(section_type, section_number, f"{addr:08X}", f"{size:08X}")

            console.print(Panel(table, title=f"[bold]{partition.get_readable_part_type()}[/bold]", expand=False))
