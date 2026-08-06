from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, NoReturn, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.tree import Tree

from wiithon.disc.structs.partition_entry import WiiPartitionEntry

from io import BytesIO
from wiithon import Rarc
from wiithon import Yaz0

from wiithon.disc.reader import WiiIsoReader


class DiscPartType(str, Enum):
    data = "data"
    update = "update"
    channel = "channel"

app = typer.Typer(help="Wii ISO patching and inspection tool.")
iso_app = typer.Typer(help="Operations on Wii ISO files.")
dol_app = typer.Typer(help="Operations on DOL.")
rarc_app = typer.Typer(help="Operations on Rarc files.")

app.add_typer(iso_app,  name="iso")
app.add_typer(rarc_app, name="rarc")
app.add_typer(dol_app, name="dol")

console = Console()
err_console = Console(stderr=True, style="bold red")

# Helpers
def _abort(msg: str) -> NoReturn:
    err_console.print(f"Error: {msg}")
    raise typer.Exit(code=1)

def _require_file(path: Path) -> None:
    if not path.exists():
        _abort(f"{path} does not exist.")
    if not path.is_file():
        _abort(f"{path} is not a file.")

def _select_partitions(
    reader: WiiIsoReader,
    partition_type: Optional[DiscPartType],
) -> list[WiiPartitionEntry]:
    """Return the partition matching the type or all if none"""
    if partition_type is None:
        return list(reader.partitions)

    wanted = DiscPartType[partition_type.name.upper()]
    candidates = [p for p in reader.partitions if p.part_type == wanted]
    if not candidates:
        _abort(f"No {partition_type.name} partition found.")

    return candidates

def _read_rarc(path: Path) -> Rarc:
    """Read a RARC archive, transparently decompressing Yaz0 if needed."""
    data = path.read_bytes()
    if data[:4] == b"Yaz0":
        data = Yaz0.read(BytesIO(data)).data

    return Rarc.read(BytesIO(data))

#################################
##########   ISO    #############
#################################
# iso info
@iso_app.command("info")
def iso_info(
    iso: Annotated[Path, typer.Argument(help="Path to the Wii ISO.")],
) -> None:
    """Display metadata from a Wii ISO disc header."""
    _require_file(iso)

    from wiithon.disc.reader import WiiIsoReader

    with WiiIsoReader(str(iso)) as reader:
        h = reader.disc_header

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="bold cyan")
        table.add_column()

        table.add_row("Game ID",    h.game_id.decode("ascii").strip("\x00"))
        table.add_row("Title",      h.game_title.strip())
        table.add_row("Disc",       str(h.disc_num))
        table.add_row("Version",    str(h.disc_version))

        parts = ", ".join(p.get_readable_part_type().upper() for p in reader.partitions)
        table.add_row("Partitions", parts)

        console.print(Panel(table, title=f"[bold]{iso.name}[/bold]", expand=False))

@iso_app.command("list")
def iso_list(
        iso: Annotated[Path, typer.Argument(help="Path to the Wii ISO.")],
        partition_type: Annotated[Optional[DiscPartType], typer.Option("--partition", "-p", help="Choose the partition type to list")] = None,
        tree: Annotated[bool, typer.Option("--tree", "-t", help="Display as a tree")] = False,
) -> None:
    """List all files from a partition"""
    _require_file(iso)

    from wiithon.disc.reader import WiiIsoReader

    with WiiIsoReader(str(iso)) as reader:
        for p in _select_partitions(reader, partition_type):
            files = reader.open_partition(p).list_files()
            label = p.get_readable_part_type()

            if tree:
                _print_tree(files, label)
            else:
                table = Table("Path")
                for f in files:
                    table.add_row(f)
                console.print(table)

            console.print(f"\n[bold]{len(files)}[/bold] file(s)")

def _print_tree(paths: list[str], partition_type: str) -> None:
    root = Tree(f"[bold cyan]{partition_type.upper()} partition[/bold cyan]")
    nodes: dict[str, Tree] = {}

    for path in sorted(paths):
        parts = path.split("/")
        parent = root
        for i, part in enumerate(parts[:-1]):
            key = "/".join(parts[: i + 1])
            if key not in nodes:
                nodes[key] = parent.add(f"[blue]{part}/[/blue]")
            parent = nodes[key]
        parent.add(parts[-1])

    console.print(root)

# TODO: Adding an option to extract sys files (dol, bnr, etc.)
@iso_app.command("extract")
def iso_extract(
        iso: Annotated[Path, typer.Argument(help="Path to the Wii ISO.")],
        dest: Annotated[Path, typer.Argument(help="Output directory.")],
        partition_type: Annotated[
            Optional[DiscPartType], typer.Option("--partition", "-p", help="Choose the partition type to list")
        ] = None
) -> None:
    """Extract all files from a partition"""
    _require_file(iso)
    dest.mkdir(parents=True, exist_ok=True)

    from wiithon.disc.reader import WiiIsoReader

    with WiiIsoReader(str(iso)) as reader:
        total = 0
        for p in _select_partitions(reader, partition_type):
            root = dest / p.get_readable_part_type()
            partition = reader.open_partition(p)
            files = partition.list_files()
            label = p.get_readable_part_type()

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("{task.completed}/{task.total}"),
                TimeElapsedColumn()
            ) as progress:
                task = progress.add_task(f"Extracting {label} partition from {iso}...", total=len(files))
                for path in files:
                    out = root / path
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_bytes(partition.read_file(path))
                    progress.advance(task)

            total += len(files)
            console.print(f"[green]ヾ(≧▽≦*)o[/green] Extracted {len(files)} file(s) to [bold]{root}[/bold]")

    console.print(f"\n[bold]{total}[/bold] file(s) extracted, yeiii (p≧w≦q)")

#################################
##########   DOL    #############
#################################
@dol_app.command("caves")
def dol_caves(
        iso: Annotated[Path, typer.Argument(help="Path to the Wii ISO")],
        min_size: Annotated[int, typer.Option("--min-size", "-m", help="The minimum size of the cave")] = 0x20,
        partition_type: Annotated[
            Optional[DiscPartType], typer.Option("--partition", "-p", help="Choose the partition type to list")
        ] = None
) -> None:
    """Find all code caves in a dol file"""
    _require_file(iso)

    from wiithon.disc.reader import WiiIsoReader

    with WiiIsoReader(str(iso)) as reader:
        for partition in _select_partitions(reader, partition_type):
            part = reader.open_partition(partition)
            dol = part.read_dol()
            table = Table("Section type", "Section number", "Start address", "Length")

            for section, addr, size in dol.find_code_caves(min_size):
                sections = section.split("[")
                section_type = sections[0]
                section_number = sections[1].split("]")[0]
                table.add_row(section_type, section_number, f"{addr:08X}", f"{size:08X}")

            console.print(Panel(table, title=f"[bold]{partition.get_readable_part_type()}[/bold]", expand=False))


#################################
##########   RARC   #############
#################################
@rarc_app.command("info")
def rarc_infos(
    rarc: Annotated[Path, typer.Argument(help="Path to the RARC archive.")],
) -> None:
    """Print information and list files about a RARC archive"""
    _require_file(rarc)
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
    _require_file(rarc)
    dest.mkdir(parents=True, exist_ok=True)
    from wiithon.formats.rarc import NodeAttribute
    arc = _read_rarc(rarc)
    arc.extract_to(str(dest))

    count = sum(1 for e in arc.entries if e.file_id != 0xFFFF and not e.attributes & NodeAttribute.DIRECTORY)
    console.print(f"[green](★‿★)[/green] Extracted {count} file(s) to [bold]{dest}[/bold]")

@rarc_app.command("pack")
def rarc_pack(
    src:      Annotated[Path, typer.Argument(help="Directory to pack.")],
    output:   Annotated[Path, typer.Argument(help="Output .arc file.")],
    compress: Annotated[bool, typer.Option("--yaz0", "-z", help="Compress output with Yaz0.")] = False,
) -> None:
    """Pack a directory into a RARC archive."""
    if not src.is_dir():
        _abort(f"{src} is not a directory.")

    # TODO: implement a rarc builder from folder

    console.print("[yellow]Not yet implemented.[/yellow]")
    raise typer.Exit(code=1)

if __name__ == "__main__":
    app()