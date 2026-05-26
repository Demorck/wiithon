from typing import Callable, Optional

from file_system_table.FST import FST
from file_system_table.FSTNode import FSTFile
from file_system_table.Operations import add_node, remove_node
from helpers.Enums import WiiPartType
from file_helper.dol import DOL
from WiiIsoReader import WiiIsoReader
from builder.WiiDiscBuilder import WiiDiscBuilder
from builder.CopyBuilder import CopyBuilder


class WiiIsoPatcher:
    def __init__(self, src_path: str):
        self.src_path = src_path
        self.reader: Optional[WiiIsoReader] = None

        self.data_partition = None # TODO: currently doing for data partition, may need a change
        self.dol_modifier: Optional[Callable[[DOL], None]] = None

        self.file_replacements: dict[str, bytes] = {}
        self.fst_modifier: Optional[Callable[[FST], None]] = None
        self.files_to_add: dict[str, bytes] = {}
        self.files_to_remove: list[str] = []

    def __enter__(self) -> "WiiIsoPatcher":
        self.reader = WiiIsoReader(self.src_path)
        self.reader.__enter__()
        self.data_partition = self.reader.open_partition(self.reader.get_data_partition())
        return self

    def __exit__(self, *args) -> None:
        if self.reader:
            self.reader.__exit__(*args)

    def modify_fst(self, fn: Callable[[FST], None]) -> None:
        self.fst_modifier = fn

    def add_file(self, path: str, data: bytes) -> None:
        key = path.strip("/")
        self.files_to_add[key] = data
        self.file_replacements[key] = data

    def remove_file(self, path: str) -> None:
        key = path.strip("/")
        self.files_to_remove.append(key)

    def replace_file(self, path: str, data: bytes) -> None:
        self.file_replacements[path.strip("/")] = data

    def list_files(self) -> list[str]:
        return self.data_partition.list_files()

    def read_file(self, path: str) -> bytes:
        return self.data_partition.read_file(path)

    def patch_dol(self, fn: Callable[[DOL], None]) -> None:
        self.dol_modifier = fn

    def read_dol(self) -> DOL:
        return self.data_partition.read_dol()

    def get_infos(self) -> dict:
        header = self.reader.disc_header
        return {
            "game_id"    : header.game_id.decode("ascii").strip("\x00"),
            "title"      : header.game_title,
            "disc_number": header.disc_num,
            "version"    : header.disc_version
        }

    def build(self, output_path: str, progress_cb=None) -> None:
        builder = WiiDiscBuilder(self.reader.disc_header, self.reader.region)

        with open(output_path, "w+b") as dest:
            for entry in self.reader.partitions:
                is_data = entry.part_type == WiiPartType.DATA
                copy_builder = CopyBuilder(
                    self.reader,
                    entry,
                    fst_modifier=self._build_fst_modifier() if is_data else None,
                    dol_modifier=self.dol_modifier if is_data else None,
                    file_overrides=self.file_replacements if is_data else None,
                )
                builder.add_partition(dest, copy_builder, progress_cb)

            builder.finish(dest)

    def _build_fst_modifier(self) -> Optional[Callable[[FST], None]]:
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