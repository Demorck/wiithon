from __future__ import annotations

import sys

import typer
from pathlib import Path
from typing import Annotated, Optional

from rich.markup import escape
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.tree import Tree

from wiithon.cli._common import PartTypeChoice, console, require_file, select_partitions, abort
from wiithon import WiiIsoReader, FSTDirectory, FSTFile

iso_app = typer.Typer(help="Operations on Wii ISO files.")

_HEXDUMP_WIDTH = 16

def _find_in_partitions(reader, entries, path: str):
    """Return (partition, node) for the first partition containing path"""
    for entry in entries:
        partition = reader.open_partition(entry)
        node = partition.fst.find_node(path)
        if node is not None:
            return partition, node

    abort(f"{path} not found in the selected partition(s).")

def _extract_node(partition, node, path: str, dest: Path) -> int:
    """Write node under dest, rooted at its own name. Return the file count"""
    if isinstance(node, FSTFile):
        out = dest / node.name
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(partition.read_file(path))
        return 1

    written = 0
    for relative in partition.list_files(node):
        out = dest / node.name / relative
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(partition.read_file(f"{path}/{relative}"))
        written += 1

    return written

def _print_hexdump(data: bytes, limit: int) -> None:
    shown = data[:limit] if limit else data

    for offset in range(0, len(shown), _HEXDUMP_WIDTH):
        chunk = shown[offset:offset + _HEXDUMP_WIDTH]
        hexa = " ".join(f"{b:02x}" for b in chunk).ljust(_HEXDUMP_WIDTH * 3 - 1)
        text = "".join(chr(b) if 0x20 <= b < 0x7F else "." for b in chunk)
        console.print(f"[dim]{offset:08x}[/dim]  {hexa}  [cyan]{escape(text)}[/cyan]")

    if limit and len(data) > limit:
        console.print(f"\n[dim]... {len(data) - limit} more byte(s), use -n 0 to print everything[/dim]")

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

@iso_app.command("info")
def iso_info(
    iso: Annotated[Path, typer.Argument(help="Path to the Wii ISO.")],
) -> None:
    """Display metadata from a Wii ISO disc header."""
    require_file(iso)

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
    partition_type: Annotated[Optional[PartTypeChoice], typer.Option("--partition", "-p", help="Choose the partition type to list")] = None,
    tree: Annotated[bool, typer.Option("--tree", "-t", help="Display as a tree")] = False,
) -> None:
    """List all files from a partition"""
    require_file(iso)

    with WiiIsoReader(str(iso)) as reader:
        for p in select_partitions(reader, partition_type):
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

# TODO: Adding an option to extract sys files (dol, bnr, etc.)
@iso_app.command("extract")
def iso_extract(
    iso: Annotated[Path, typer.Argument(help="Path to the Wii ISO.")],
    dest: Annotated[Path, typer.Argument(help="Output directory.")],
    partition_type: Annotated[
        Optional[PartTypeChoice], typer.Option("--partition", "-p", help="Choose the partition type to list")
    ] = None,
    file: Annotated[
        Optional[str], typer.Option("--file", "-f", help="Extract only this file or directory.")
    ] = None,
) -> None:
    """Extract all files from a partition"""
    require_file(iso)
    dest.mkdir(parents=True, exist_ok=True)

    if file is not None:
        target = file.strip("/").replace("\\", "/")
        with WiiIsoReader(str(iso)) as reader:
            entries = select_partitions(reader, partition_type)
            partition, node = _find_in_partitions(reader, entries, target)
            written = _extract_node(partition, node, target, dest)

        console.print(f"[green](★‿★)[/green] Extracted {written} file(s) to [bold]{dest}[/bold]")
        return

    with WiiIsoReader(str(iso)) as reader:
        total = 0
        for p in select_partitions(reader, partition_type):
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


@iso_app.command("cat")
def iso_cat(
        iso: Annotated[Path, typer.Argument(help="Path to the Wii ISO.")],
        path: Annotated[str, typer.Argument(help="Path of the file inside the partition.")],
        partition_type: Annotated[
            Optional[PartTypeChoice], typer.Option("--partition", "-p", help="Restrict the lookup to this partition type")
        ] = None,
        limit: Annotated[int, typer.Option("--bytes", "-n", help="Bytes to show in hexdump mode (0 = all).")] = 512,
) -> None:
    """Print one file from a partition: hexdump on a terminal, raw bytes when piped"""
    require_file(iso)
    path = path.strip("/").replace("\\", "/")

    with WiiIsoReader(str(iso)) as reader:
        entries = select_partitions(reader, partition_type)
        partition, node = _find_in_partitions(reader, entries, path)

        if isinstance(node, FSTDirectory):
            abort(f"{path} is a directory - use `wiithon iso list` to browse it")

        data = partition.read_file(path)

    if sys.stdout.isatty():
        _print_hexdump(data, limit)
    else:
        sys.stdout.buffer.write(data)