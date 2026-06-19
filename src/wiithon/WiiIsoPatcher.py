"""
Provides the WiiIsoPatcher class, a high-level API designed to open, modify,
and rebuild Nintendo Wii ISO images

This module acts as the primary orchestrator for scripts needing to inject custom
files, patch executables (DOL), alter the File System Table (FST), and modify metadata
like the game title or banner. It handles the extraction and rebuilding pipelines
seamlessly, specifically focusing on the data partition (at least, for now)
"""

from typing import Callable, Optional, Any
from io import BytesIO

from wiithon.file_helper.bnr import BNR
from wiithon.file_system_table.FST import FST
from wiithon.file_system_table.FSTNode import FSTFile
from wiithon.file_system_table.Operations import add_node, remove_node
from wiithon.helpers.Enums import WiiPartType
from wiithon.file_helper.dol import DOL
from wiithon.WiiIsoReader import WiiIsoReader
from wiithon.builder.WiiDiscBuilder import WiiDiscBuilder
from wiithon.builder.CopyBuilder import CopyBuilder


class WiiIsoPatcher:
    """
    High-level utility to patch Wii ISO files

    This class is intended to be used as a context manager (using the `with` statement)
    to automatically handle opening and closing the ISO reader

    Note:
        Currently, this patcher focuses only on the DATA partition of the ISO
    """

    src_path: str
    """Path to the source ISO file."""

    reader: Optional[WiiIsoReader]
    """Internal reader for the ISO file (initialized within the context manager)."""

    data_partition: Any
    """Reference to the open data partition being modified."""

    dol_modifier: Optional[Callable[[DOL], None]]
    """Callback function used to modify the main executable (DOL) during the build process."""

    file_replacements: dict[str, bytes]
    """Dictionary mapping internal paths to their new binary data for file replacements."""

    fst_modifier: Optional[Callable[[FST], None]]
    """Callback function used to perform manual, direct modifications to the FST."""

    files_to_add: dict[str, bytes]
    """Dictionary mapping internal paths to raw bytes for newly injected files."""

    files_to_remove: list[str]
    """List of internal file paths marked for deletion from the FST."""

    def __init__(self, src_path: str):
        """
        Initializes the patcher with the target ISO path

        Args:
            src_path: The file system path to the source Wii ISO
        """
        self.src_path = src_path
        self.reader = None

        self.data_partition = None # TODO: currently doing for data partition, may need a change
        self.dol_modifier = None

        self.file_replacements = {}
        self.fst_modifier = None
        self.files_to_add = {}
        self.files_to_remove = []

    def __enter__(self) -> "WiiIsoPatcher":
        self.reader = WiiIsoReader(self.src_path)
        self.reader.__enter__()
        self.data_partition = self.reader.open_partition(self.reader.get_data_partition())
        return self

    def __exit__(self, *args) -> None:
        if self.reader:
            self.reader.__exit__(*args)

    def modify_fst(self, fn: Callable[[FST], None]) -> None:
        """
        Registers a callback to modify the File System Table

        Args:
            fn: A callable taking the FST object, allowing in-place modifications
        """
        self.fst_modifier = fn

    def add_file(self, path: str, data: bytes) -> None:
        """
        Schedules a new file to be added to the partition

        Args:
            path: The internal destination path for the new file
            data: The raw binary data of the new file

        Examples:
            >>> with WiiIsoPatcher("/path/to/iso") as patcher:
            ...     patcher.add_file("/path/to/file", data)
            ...     patcher.build("destination/path")
            The file will be added to the partition with the correct data
        """
        key = path.strip("/")
        self.files_to_add[key] = data
        self.file_replacements[key] = data

    def remove_file(self, path: str) -> None:
        """
        Schedules a file to be removed from the partition

        If the file was previously scheduled to be added, it is simply aborted
        Otherwise, it is added to the removal list

        Args:
            path: The internal path of the file to remove


        Examples:
            >>> with WiiIsoPatcher("/path/to/iso") as patcher:
            ...     patcher.remove_file("/path/to/file")
            ...     patcher.build("destination/path")
            The file will be removed from the destination iso
        """
        key = path.strip("/")
        if key in self.files_to_add:
            self.files_to_add.pop(key)
            self.file_replacements.pop(key)
        else:
            self.files_to_remove.append(key)

    def replace_file(self, path: str, data: bytes) -> None:
        """
        Schedules an existing file to be replaced with new data

        Args:
            path: The internal path of the file to replace
            data: The new raw binary data
        """
        self.file_replacements[path.strip("/")] = data

    def list_files(self) -> list[str]:
        """
        Lists all files present in the active data partition

        Returns:
            A list of all file paths currently in the partition
        """
        return self.data_partition.list_files()

    def read_file(self, path: str) -> bytes:
        """
        Reads and returns the raw binary data of a file from the partition

        Args:
            path: The internal path of the target file

        Returns:
            The decrypted file data
        """
        return self.data_partition.read_file(path)

    def transform_file(self, path: str, fn: Callable[[bytes], bytes]) -> None:
        """
        Reads a file, applies a transformation, and schedules it for replacement

        Args:
            path: The internal path of the file to transform
            fn: A callback that receives the original bytes and returns the modified bytes
        """
        original = self.data_partition.read_file(path)
        self.replace_file(path, fn(original))

    def patch_dol(self, fn: Callable[[DOL], None]) -> None:
        """
        Registers a callback to modify the main executable (DOL) on the fly

        Args:
            fn: A callable that receives the DOL object for in-place modification
        """
        self.dol_modifier = fn

    def read_dol(self) -> DOL:
        """
        Reads and parses the main executable (DOL) of the active partition

        Returns:
            The parsed DOL object
        """
        return self.data_partition.read_dol()

    def get_infos(self) -> dict:
        """
        Extracts basic game metadata from the disc header

        Returns:
            A dictionary containing the `game_id`, `title`, `disc_number`, and `version`
        """
        header = self.reader.disc_header
        return {
            "game_id"    : header.game_id.decode("ascii").strip("\x00"),
            "title"      : header.game_title,
            "disc_number": header.disc_num,
            "version"    : header.disc_version
        }

    def modify_banner_title(self, new_title: str, language: Optional[str]) -> None:
        """
        Modifies the title displayed in the Wii Menu banner (`opening.bnr`)

        Args:
            new_title: The new title string to display
            language: The specific language slot to modify ('EN', 'FR')
        """
        bnr_bytes = self.read_file("opening.bnr")
        bnr = BNR.read(BytesIO(bnr_bytes))
        bnr.imet.set_title(new_title, language)
        self.replace_file("opening.bnr", bnr.get_bytes())

    def modify_title(self, new_title: str) -> None:
        """
        Modifies the internal disc header title

        Args:
            new_title: The new game title
        """
        self.reader.disc_header.game_title = new_title

    def modify_title_id(self, new_id: str):
        """
        Modifies the Game/Title ID in both the disc header and the ticket

        Args:
            new_id: A 6-character string representing the new game ID

        Raises:
            RuntimeError: If the provided `new_id` does not result in exactly 6 bytes
        """
        b = new_id.encode("ascii")
        if len(b) != 0x06:
            raise RuntimeError(f"Title ID needs to be 6 bytes length, got: {len(b)} with {b}")

        self.reader.disc_header.game_id = b
        self.data_partition.header.ticket.title_id = b'\x00\x01\x00\x00' + b[:4]

    def build(self, output_path: str, progress_cb: Optional[Callable[[float], None]] = None) -> None:
        """
        Assembles all changes and builds the final patched Wii ISO file

        Args:
            output_path: The file system path where the built ISO will be saved
            progress_cb: An optional callback to track the build progress (receives a float)
        """
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