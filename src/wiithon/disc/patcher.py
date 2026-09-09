from collections.abc import Callable, Iterator
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from typing import Concatenate, ParamSpec, TypeVar

from wiithon.builder.copy_source import CopyPartitionSource
from wiithon.builder.disc_builder import WiiDiscBuilder
from wiithon.disc.enums import WiiPartType
from wiithon.disc.reader import WiiIsoReader
from wiithon.exceptions import NoDataPartitionError
from wiithon.formats.archive import (
    Archive,
    Container,
    flush_archive_cache,
    resolve_read,
    resolve_write,
    unwrap_containers,
    wrap_containers,
)
from wiithon.formats.bnr import BNR
from wiithon.formats.dol import DOL
from wiithon.formats.imet import IMET_LANGUAGES
from wiithon.fst.node import FSTFile
from wiithon.fst.operations import add_node, remove_node
from wiithon.fst.tree import FST

T = TypeVar("T")
P = ParamSpec("P")

class WiiIsoPatcher:
    def __init__(self, src_path: str) -> None:
        self.src_path = src_path
        self.reader: WiiIsoReader | None = None

        self.data_partition = None
        self.dol_modifiers: list[Callable[[DOL], None]] = []

        self.file_replacements: dict[str, bytes] = {}
        self.fst_modifier: Callable[[FST], None] | None = None
        self.files_to_add: dict[str, bytes] = {}
        self.files_to_remove: list[str] = []

        self.cached_archive: tuple[str, Archive, list[Container]] | None = None

    def __enter__(self) -> "WiiIsoPatcher":
        self.reader = WiiIsoReader(self.src_path)
        try:
            self.reader.__enter__()
            entry = self.reader.get_data_partition()
            if entry is None:
                raise NoDataPartitionError(f"No DATA partition in {self.src_path}")

            self.data_partition = self.reader.open_partition(entry)

        except BaseException:
            self.reader.close()
            self.reader = None
            raise

        return self

    def __exit__(self, *args: int) -> None:
        if self.reader:
            self.reader.__exit__(*args)

    @property
    def title(self) -> str:
        return self.reader.disc_header.game_title

    @title.setter
    def title(self, title: str) -> None:
        self.reader.disc_header.game_title = title

    @property
    def title_id(self) -> str:
        return self.reader.disc_header.game_id.decode("ascii").strip("\x00")

    @title_id.setter
    def title_id(self, value: str) -> None:
        b = value.encode("ascii")
        if len(b) > 0x06:
            raise ValueError(f"Title ID is 6 bytes max, got: {len(b)} with {b}")

        b = b.ljust(0x06, b"\x00")

        self.reader.disc_header.game_id = b
        self.data_partition.header.ticket.title_id = b'\x00\x01\x00\x00' + b[:4]

    def modify_fst(self, fn: Callable[[FST], None]) -> None:
        self.fst_modifier = fn

    def add_file(self, path: str, data: bytes) -> None:
        key = path.strip("/")
        self.files_to_add[key] = data
        self.file_replacements[key] = data

    def remove_file(self, path: str) -> None:
        key = path.strip("/")
        if key in self.files_to_add:
            self.files_to_add.pop(key)
            self.file_replacements.pop(key)
        else:
            self.files_to_remove.append(key)

    def replace_file(self, path: str, data: bytes) -> None:
        key = path.strip('/')
        if self.cached_archive is not None and self.cached_archive[0] == key:
            self.cached_archive = None

        self.file_replacements[key] = data

    def list_files(self) -> list[str]:
        return self.data_partition.list_files()

    def read_file(self, path: str) -> bytes:
        return self.data_partition.read_file(path)

    @contextmanager
    def edit_as(self, path: str, cls: type[T], **kwargs: int) -> Iterator[T]:
        data, containers = unwrap_containers(resolve_read(self, path), cls)
        obj = cls.read(BytesIO(data), **kwargs)
        yield obj
        buf = BytesIO()
        obj.write(buf)
        resolve_write(self, path, wrap_containers(buf.getvalue(), containers))

    # noinspection PyTypeHints
    def patch_dol(self, fn: Callable[Concatenate[DOL, P], None], *args: P.args, **kwargs: P.kwargs) -> None:
        self.dol_modifiers.append(lambda dol: fn(dol, *args, **kwargs))

    def read_dol(self) -> DOL:
        return self.data_partition.read_dol()

    def get_banner_title(self, language: str = "English") -> str:
        bnr = BNR.read(BytesIO(self.read_file("opening.bnr")))
        return bnr.imet.titles[IMET_LANGUAGES.index(language)]

    def set_banner_title(self, new_title: str, language: str = "English") -> None:
        bnr_bytes = self.read_file("opening.bnr")
        bnr = BNR.read(BytesIO(bnr_bytes))
        bnr.imet.set_title(new_title, language)
        self.replace_file("opening.bnr", bnr.get_bytes())

    def build(self, output_path: str, progress_cb: Callable | None = None) -> None:
        flush_archive_cache(self)
        builder = WiiDiscBuilder(self.reader.disc_header, self.reader.region)

        output_path = Path(output_path)
        with output_path.open("w+b") as dest:
            for entry in self.reader.partitions:
                is_data = entry.part_type == WiiPartType.DATA
                copy_builder = CopyPartitionSource(
                    self.reader,
                    entry,
                    fst_modifier=self._build_fst_modifier() if is_data else None,
                    dol_modifiers=self.dol_modifiers if is_data else None,
                    file_overrides=self.file_replacements if is_data else None,
                )
                builder.add_partition(dest, copy_builder, progress_cb)

            builder.finish(dest)

    def _build_fst_modifier(self) -> Callable[[FST], None] | None:
        user_modification = self.fst_modifier
        files_to_add = dict(self.files_to_add)
        files_to_remove = list(self.files_to_remove)

        if not user_modification and not files_to_add and not files_to_remove:
            return None

        def modifier(fst: FST) -> None:
            if user_modification:
                user_modification(fst)
            for path, data in files_to_add.items():
                parts = path.split("/")
                node = FSTFile(name=parts[-1], offset=0, length=len(data))
                add_node(fst.entries, parts[:-1], node)
            for path in files_to_remove:
                remove_node(fst.entries, path.split("/"))

        return modifier